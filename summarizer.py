import json
import logging
from typing import Optional

from providers import LLMProvider

log = logging.getLogger(__name__)

_HIGHLIGHT_SYSTEM = """\
당신은 글로벌 제약·바이오·AI 산업 전문 애널리스트입니다.
주어진 본문(또는 논문 abstract)을 한국어 bullet point로 요약하세요.

## 출력 규칙
- title_kr: 한국어 제목 (자연스럽게 의역)
- summary: 핵심 내용을 bullet point 5~10개로 정리.
  각 bullet은 "• "로 시작하고 한 줄로 작성.
  수치·금액·임상 단계·딜 구조 등 BD 판단에 유용한 디테일을 포함할 것.

반드시 JSON으로만 응답:
{{"title_kr": "...", "summary": "• ...\n• ...\n• ..."}}
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

빅파마·바이오텍의 주목할 움직임 (딜·투자·파트너십·임상 중심, 3~5개 bullet).
각 bullet에 회사명과 금액/규모 포함.

반드시 JSON으로만 응답:
{{"movements": ["..."]}}
"""

_DIGEST_USER = """\
오늘의 항목 목록:
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
    user = _DIGEST_USER.format(items_json=items_json)
    return _safe_call(provider, _DIGEST_SYSTEM, user, label="digest")
