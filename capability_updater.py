"""
LG AI연구원의 바이오 분야 최신 역량을 웹 검색으로 수집·추출하여
data/lg_capabilities.json에 캐싱합니다 (7일 TTL).
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from providers import LLMProvider

log = logging.getLogger(__name__)

_CACHE_PATH = Path("data/lg_capabilities.json")
_REFRESH_DAYS = 7

_SEARCH_QUERIES = [
    '"LG AI Research" bio drug discovery OR protein design OR antibody OR pathology 2024 2025',
    '"LG AI연구원" 바이오 신약 단백질 항체 디지털병리 2024 2025',
    '"LG AI Research" spatial transcriptomics OR AlphaFold OR cyclic peptide OR Alzheimer',
    'site:lgresearch.ai bio OR biotech OR protein OR drug OR antibody',
    '"LG AI Research" publication paper biomedical 2024',
]

_EXTRACT_SYSTEM = """\
당신은 LG AI연구원의 바이오 분야 연구 역량을 정리하는 분석가입니다.
아래는 웹 검색으로 수집한 LG AI연구원 관련 텍스트입니다.
이 텍스트에서 LG AI연구원의 바이오 분야 기술 역량, 최신 연구 성과, 보유 플랫폼을 추출하여 정리하세요.
확인된 사실만 작성하고, 검색 결과에 없는 내용은 추가하지 마세요.

반드시 JSON으로만 응답:
{"capabilities": ["기술명 — 한 줄 설명", ...], "recent_works": ["제목 (연도)", ...], "platforms": ["플랫폼명 — 설명", ...]}
"""

_DEFAULT_CAPABILITIES = {
    "capabilities": [
        "항체 설계 — AI 기반 항체 구조 예측 및 서열 최적화",
        "단백질 구조 예측·설계 — 생성 AI 기반 de novo 단백질 설계",
        "디지털 병리학 — Whole Slide Image AI 분석 및 진단 지원",
        "공간전사체 분석 — Spatial omics 데이터 통합 AI 분석",
        "사이클로펩타이드 — 매크로사이클 펩타이드 약물 설계",
        "AI 신약 개발 플랫폼 — 멀티모달 AI 기반 신약 후보 발굴·최적화",
        "알츠하이머·신경퇴행 — 신경과학 AI 모델 연구",
    ],
    "recent_works": [],
    "platforms": [],
}


def _load_cache() -> Optional[dict]:
    if not _CACHE_PATH.exists():
        return None
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        updated_at_str = data.get("updated_at", "2000-01-01T00:00:00+00:00")
        updated_at = datetime.fromisoformat(updated_at_str)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age = datetime.now(tz=timezone.utc) - updated_at
        if age > timedelta(days=_REFRESH_DAYS):
            log.info(f"LG capabilities cache expired ({age.days}d old), refreshing")
            return None
        log.info(f"LG capabilities loaded from cache (age: {age.days}d)")
        return data
    except Exception as e:
        log.warning(f"Cache load failed: {e}")
        return None


def _save_cache(data: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    _CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"LG capabilities cached → {_CACHE_PATH}")


def _search_web(queries: list[str]) -> str:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        log.warning("duckduckgo_search not installed — skipping web search")
        return ""

    collected: list[str] = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = ddgs.text(q, max_results=5)
                    for r in results:
                        snippet = (
                            f"[{r.get('title', '')}]\n"
                            f"{r.get('body', '')}\n"
                            f"{r.get('href', '')}"
                        )
                        collected.append(snippet)
                except Exception as e:
                    log.debug(f"Query failed ({q!r}): {e}")
    except Exception as e:
        log.warning(f"DDGS session failed: {e}")

    log.info(f"Web search collected {len(collected)} snippets across {len(queries)} queries")
    return "\n\n---\n\n".join(collected)


def _extract_with_llm(raw_text: str, provider: LLMProvider) -> Optional[dict]:
    if not raw_text.strip():
        return None
    try:
        raw = provider.complete(
            _EXTRACT_SYSTEM,
            f"수집된 텍스트:\n{raw_text[:8_000]}",
            json_mode=True,
        )
        result = json.loads(raw)
        # 최소 구조 검증
        if not isinstance(result.get("capabilities"), list):
            return None
        return result
    except Exception as e:
        log.warning(f"LLM capability extraction failed: {e}")
        return None


def get_lg_capabilities(provider: LLMProvider) -> dict:
    """캐시가 유효하면 반환, 만료됐으면 웹 검색 후 LLM 추출하여 갱신."""
    cached = _load_cache()
    if cached:
        return cached

    log.info("=== LG AI 역량 웹 검색 시작 ===")
    raw_text = _search_web(_SEARCH_QUERIES)
    extracted = _extract_with_llm(raw_text, provider)

    if extracted:
        # 기본값에 검색 결과를 병합: 기본 역량은 유지하고 새 항목 추가
        merged = _merge_with_defaults(extracted)
        _save_cache(merged)
        log.info(
            f"LG capabilities updated — "
            f"{len(merged.get('capabilities', []))} capabilities, "
            f"{len(merged.get('recent_works', []))} recent works"
        )
        return merged
    else:
        log.warning("Extraction failed — using default capabilities")
        return _DEFAULT_CAPABILITIES


def _merge_with_defaults(extracted: dict) -> dict:
    """추출된 결과와 기본값을 병합. 기본 역량 항목은 항상 포함."""
    default_caps = {c.split(" — ")[0] for c in _DEFAULT_CAPABILITIES["capabilities"]}
    merged_caps = list(_DEFAULT_CAPABILITIES["capabilities"])

    for c in extracted.get("capabilities", []):
        name = c.split(" — ")[0].strip()
        if name not in default_caps:
            merged_caps.append(c)

    return {
        "capabilities": merged_caps,
        "recent_works": extracted.get("recent_works", []),
        "platforms": extracted.get("platforms", []),
    }


def format_for_prompt(caps: dict) -> str:
    """프롬프트에 삽입할 형식으로 변환."""
    lines: list[str] = []

    if caps.get("capabilities"):
        lines.append("【보유 기술 역량】")
        for c in caps["capabilities"]:
            lines.append(f"• {c}")

    if caps.get("recent_works"):
        lines.append("\n【최신 연구·성과】")
        for w in caps["recent_works"]:
            lines.append(f"• {w}")

    if caps.get("platforms"):
        lines.append("\n【보유 플랫폼·툴】")
        for p in caps["platforms"]:
            lines.append(f"• {p}")

    return "\n".join(lines)
