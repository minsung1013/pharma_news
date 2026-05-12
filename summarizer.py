import json
import logging
from typing import Optional

from providers import LLMProvider

log = logging.getLogger(__name__)

_HIGHLIGHT_SYSTEM = """\
당신은 글로벌 제약·바이오·AI 산업 전문 애널리스트입니다.
주어진 본문(또는 논문 abstract)을 한국어로 깊이 있게 요약하세요.

## 출력 규칙
- title_kr: 한국어 제목 (자연스럽게 의역)
- summary: 본문 핵심 요약 (수치·임상 단계·기술 메커니즘·딜 구조 등 유용한 디테일 포함)

반드시 JSON으로만 응답:
{{"title_kr": "...", "summary": "..."}}
"""

_HIGHLIGHT_USER = """\
원문 제목: {title}
타입: {type}
카테고리: {category}
매칭 키워드: {matched_keywords}

본문:
{body}
"""

_DIGEST_SYSTEM = """\
당신은 글로벌 제약·바이오·AI 산업 전문 애널리스트입니다.
오늘 수집된 항목 전체를 분석해 한국어로 작성하세요.

어제 트렌드가 제공된 경우, 그 흐름과 맥락을 이어받아 오늘의 트렌드를 작성하세요.
단순 나열이 아니라 산업의 방향성이 느껴지도록 서술하세요.

1. trend: 핵심 트렌드 (4~6문장). 어제 흐름과 연결하여 산업 맥락이 유지되도록 작성.
   수치·딜·기술 키워드를 포함해 구체적으로 서술할 것.
2. movements: 빅파마·바이오텍의 주목할 움직임 (딜·투자·파트너십·임상 중심, 3~5개 bullet).
   각 bullet에 회사명과 금액/규모 포함.

반드시 JSON으로만 응답:
{{"trend": "...", "movements": ["..."]}}
"""

_DIGEST_USER = """\
{prev_section}오늘의 항목 목록:
{items_json}
"""


def _safe_call(
    provider: LLMProvider,
    system: str,
    user: str,
    label: str,
) -> Optional[dict]:
    for attempt in range(2):
        try:
            raw = provider.complete(system, user, json_mode=True)
            return json.loads(raw)
        except Exception as e:
            log.warning(f"[{label}] attempt {attempt + 1} failed: {e}")
    log.error(f"[{label}] gave up after 2 attempts")
    return None


def summarize_highlight(
    article: dict,
    body: str,
    provider: LLMProvider,
) -> Optional[dict]:
    user = _HIGHLIGHT_USER.format(
        title=article.get("title", ""),
        type=article.get("type", ""),
        category=article.get("category", ""),
        matched_keywords=", ".join(article.get("matched_keywords", [])),
        body=body[:7_000],
    )
    label = article.get("title", "")[:50]
    return _safe_call(provider, _HIGHLIGHT_SYSTEM, user, label=label)


def generate_digest(
    articles: list[dict],
    provider: LLMProvider,
    prev_trend: Optional[str] = None,
) -> Optional[dict]:
    items_json = json.dumps(
        [
            {
                "title":          a["title"],
                "category":       a.get("category", ""),
                "korean_summary": a.get("korean_summary", ""),
            }
            for a in articles
        ],
        ensure_ascii=False,
    )
    prev_section = (
        f"어제의 핵심 트렌드 (맥락 참고용):\n{prev_trend}\n\n"
        if prev_trend else ""
    )
    user = _DIGEST_USER.format(prev_section=prev_section, items_json=items_json)
    return _safe_call(provider, _DIGEST_SYSTEM, user, label="digest")
