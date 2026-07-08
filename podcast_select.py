"""팟캐스트 '중요 뉴스 원문 낭독' 선별 로직.

요청 규칙: **AI 관련 / 인수·M&A / 협업·파트너십** 기사를 우선한다.
classifier 가 이미 부여한 신호를 재활용해 점수화한다:
  - highlight_score (0~10): 관심 카테고리 부합도
  - category / matched_keywords: 주제 라벨·키워드
  - organizations[].role: acquirer/target(M&A), partner/investor(협업·투자)

낭독 분량(목표 시간) 산정을 위한 길이 추정 유틸도 함께 제공한다.
"""
from __future__ import annotations

# ── 규칙 사전 ────────────────────────────────────────────────────────────────
_AI_KEYWORDS = {
    "artificial intelligence", "ai", "machine learning", "deep learning",
    "ai drug discovery", "ai diagnostics", "foundation model",
}
_AI_CATEGORY_HINT = ("ai", "machine learning", "digital patholog", "computational")

_MNA_ROLES = {"acquirer", "target"}
_PARTNER_ROLES = {"partner", "investor"}
_MNA_CATEGORY_HINT = ("m&a", "acquisition", "merger", "buyout", "takeover")
_PARTNER_CATEGORY_HINT = (
    "partnership", "collaboration", "licensing", "license",
    "funding", "investment", "alliance", "deal",
)

# 점수 가중치
_W_AI = 4
_W_MNA = 5
_W_PARTNER = 3


def _kw_lower(a: dict) -> set[str]:
    return {str(k).lower() for k in a.get("matched_keywords", []) or []}


def _roles(a: dict) -> set[str]:
    return {str(o.get("role", "")).lower() for o in a.get("organizations", []) or []}


def podcast_score(a: dict) -> int:
    """규칙 기반 우선순위 점수. 부여 근거는 a['_podcast_reasons'] 에 기록."""
    score = int(a.get("highlight_score", 0) or 0)
    cat = (a.get("category") or "").lower()
    kws = _kw_lower(a)
    roles = _roles(a)

    reasons: list[str] = []
    if kws & _AI_KEYWORDS or any(h in cat for h in _AI_CATEGORY_HINT):
        score += _W_AI
        reasons.append("AI")
    if roles & _MNA_ROLES or any(h in cat for h in _MNA_CATEGORY_HINT):
        score += _W_MNA
        reasons.append("M&A")
    if roles & _PARTNER_ROLES or any(h in cat for h in _PARTNER_CATEGORY_HINT):
        score += _W_PARTNER
        reasons.append("협업")

    a["_podcast_reasons"] = reasons
    a["_podcast_score"] = score
    return score


def rank_for_podcast(dedup_reps: list[dict]) -> list[dict]:
    """dedup 대표 기사들을 규칙 점수 내림차순으로 정렬해 반환.

    동점 시 highlight_score, 그다음 원래 순서(최신성)를 유지.
    """
    indexed = list(enumerate(dedup_reps))
    return [
        a for _, a in sorted(
            indexed,
            key=lambda t: (
                podcast_score(t[1]),
                int(t[1].get("highlight_score", 0) or 0),
                -t[0],
            ),
            reverse=True,
        )
    ]


# ── 낭독 길이 추정 ────────────────────────────────────────────────────────────
# edge-tts +0% 기준 대략치: 한국어 ≈ 5.0자/초(≈300자/분), 영어 ≈ 2.5단어/초(≈150단어/분)
_KO_CHARS_PER_SEC = 5.0
_EN_WORDS_PER_SEC = 2.5


def est_seconds(text: str, lang: str = "ko") -> float:
    if not text:
        return 0.0
    if lang == "en":
        return len(text.split()) / _EN_WORDS_PER_SEC
    return len(text) / _KO_CHARS_PER_SEC
