import json
import logging

from providers import LLMProvider

log = logging.getLogger(__name__)

_SYSTEM = """\
당신은 글로벌 제약·바이오·AI 산업의 뉴스/논문 큐레이터입니다.
입력으로 오늘 수집된 항목 목록(JSON)이 주어집니다. 각 항목에 대해 다음을 수행하세요.

1. korean_summary: RSS 요약을 기반으로 한국어 한 문장(40자 이내) 요약.
   - 주어 + 행동 중심, 수치·금액 포함, 마침표로 끝낼 것.
2. category: 핵심 주제 라벨을 영문 단답으로 부여.
   예: "Digital Pathology", "Big Pharma Deal", "Antibody Engineering",
       "AI Drug Discovery", "Clinical Trial", "Protein Design",
       "Funding", "Regulation", "Drug Approval".
3. highlight_score: 0~10 정수. 아래 6개 카테고리 해당 여부로 평가:
   [핵심 카테고리 — 해당 시 7~10점]
   - AI 신약 개발: AI/ML을 활용한 신약 발굴·설계·임상 예측
   - 디지털 병리학: digital pathology, computational pathology, WSI, 슬라이드 AI 분석
   - 단백질 구조 예측·설계: AlphaFold, RoseTTAFold, de novo protein, protein language model
   - 항체 설계: antibody design/engineering, bispecific antibody, ADC
   - 알츠하이머·신경퇴행: Alzheimer, amyloid, tau, dementia, neurodegeneration
   - 빅파마 합병·파트너십·신사업 전략: M&A, acquisition, licensing deal, strategic partnership, 신규 플랫폼 발표
   [관련성 있으나 핵심 아님 — 3~6점]
   [무관 — 0~2점]
4. matched_keywords: 관심 키워드 중 부합하는 것들의 배열 (없으면 빈 배열).
5. dedup_group_id: 동일 사건/주제를 다룬 항목들에 같은 양의 정수 ID 부여.
   완전히 다른 주제는 각자 고유 ID. 가장 정보량이 많은 항목을 그룹 대표로.
6. organizations: 기사·논문의 주체 조직을 모두 추출.
   - name: 정식 명칭 (예: "Roche", "PathAI", "MIT Broad Institute")
   - org_type: pharma | biotech | academic | startup | hospital | govt | other
   - role: acquirer | target | partner | investor | author_lab | developer | regulator | subject | other
     (M&A: 인수자=acquirer, 피인수=target. 파트너십: 양측=partner.
      투자: 투자자=investor, 피투자=target. 논문 1저자/교신저자 소속=author_lab.
      그 외 기사 주인공=subject.)
   - 특정 조직이 주체가 아닌 일반 동향 기사는 빈 배열.

관심 키워드 목록:
{keywords}

반드시 JSON으로만 응답 (다른 텍스트 없음):
{{"items": [{{"id": <int>, "korean_summary": "...", "category": "...", "highlight_score": <int 0-10>, "matched_keywords": [], "dedup_group_id": <int>, "organizations": [{{"name": "...", "org_type": "...", "role": "..."}}]}}]}}
"""

_USER = "오늘의 항목 목록:\n{articles_json}"


def _call(articles: list[dict], provider: LLMProvider, keywords: str) -> dict[int, dict]:
    payload = [
        {
            "id":      a["id"],
            "type":    a["type"],
            "source":  a["source"],
            "title":   a["title"],
            "summary": a["summary"][:600],
        }
        for a in articles
    ]
    system = _SYSTEM.format(keywords=keywords)
    user   = _USER.format(articles_json=json.dumps(payload, ensure_ascii=False))
    raw    = provider.complete(system, user, json_mode=True)
    result = json.loads(raw)
    return {item["id"]: item for item in result["items"]}


def classify(articles: list[dict], provider: LLMProvider, top_n: int = 5) -> list[dict]:
    from config import INTEREST_KEYWORDS
    keywords = ", ".join(INTEREST_KEYWORDS)

    classified: dict[int, dict] | None = None
    for attempt in range(2):
        try:
            classified = _call(articles, provider, keywords)
            break
        except Exception as e:
            log.warning(f"Classify attempt {attempt + 1} failed: {e}")
            if attempt == 1:
                raise RuntimeError("LLM classification failed after 2 attempts") from e

    enriched = []
    for a in articles:
        c = classified.get(a["id"], {})  # type: ignore[union-attr]
        enriched.append({
            **a,
            "korean_summary":   c.get("korean_summary",   a["title"]),
            "category":         c.get("category",         "Other"),
            "highlight_score":  int(c.get("highlight_score", 0)),
            "matched_keywords": c.get("matched_keywords",  []),
            "dedup_group_id":   c.get("dedup_group_id",   a["id"]),
            "organizations":    c.get("organizations",    []),
        })

    # dedup 대표 기사 중 점수 상위 top_n개만 하이라이트
    seen_dedup: set[int] = set()
    scored: list[dict] = []
    for a in sorted(enriched, key=lambda x: x["highlight_score"], reverse=True):
        gid = a.get("dedup_group_id", a["id"])
        if gid not in seen_dedup:
            seen_dedup.add(gid)
            scored.append(a)

    top_ids = {a["id"] for a in scored[:top_n]}
    for a in enriched:
        a["is_highlight"] = a["id"] in top_ids

    top_scores = [a["highlight_score"] for a in scored[:top_n]]
    log.info(f"Classification done — top {top_n} highlights (scores: {top_scores})")
    return enriched
