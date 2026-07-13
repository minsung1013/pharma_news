"""규칙 기반 뉴스 큐레이션 (LLM 없음).

수집된 기사에 대해:
  1. 키워드 카테고리 매칭 → score (가중합) + category(라벨) + matched_keywords
  2. score < SCORE_THRESHOLD 인 기사는 게이트에서 제외(drop)
  3. 제목 유사도로 중복 그룹핑(dedup_group_id) → 그룹 대표만 하이라이트 후보
  4. score 상위 TOP_HIGHLIGHTS 개(대표 기준)를 is_highlight=True
  5. gazetteer 로 등장 기관(organizations) 추출

매칭 대상은 제목 + 요약 + 본문(content) '모든 텍스트'.
"""
import logging
import re

import config as cfg

log = logging.getLogger(__name__)


# ── 매처 컴파일 ───────────────────────────────────────────────────────────────
def _has_hangul(s: str) -> bool:
    return any("가" <= c <= "힣" for c in s)


def _is_acronym(term: str) -> bool:
    letters = [c for c in term if c.isalpha()]
    return bool(letters) and len(term) <= 6 and all(c.isupper() for c in letters)


def _compile_term(term: str) -> tuple[str, object]:
    """키워드 → (kind, payload).

    kind 'sub': 한국어 등 부분일치. payload = 소문자 term.
    kind 're' : 단어경계 정규식. payload = 컴파일된 regex.
                 약어(대문자)는 대소문자 구분, 그 외는 무시.
    """
    if _has_hangul(term):
        return ("sub", term.lower())
    esc = re.escape(term)
    pattern = rf"(?<!\w){esc}(?!\w)"
    flags = 0 if _is_acronym(term) else re.IGNORECASE
    return ("re", re.compile(pattern, flags))


def _term_matches(kind: str, payload, text: str, text_lower: str) -> bool:
    if kind == "sub":
        return payload in text_lower
    return payload.search(text) is not None


def _valid_keyword(term: str) -> bool:
    """1글자 한국어 키워드는 부분일치 오탐(예: '암'→'암호화')이 심해 금지."""
    if _has_hangul(term) and len(term.strip()) < 2:
        log.warning(f"1글자 한국어 키워드 무시(오탐 위험): {term!r}")
        return False
    return True


# 카테고리 매처: [(name, weight, [(term, kind, payload), ...]), ...]
_CATEGORY_MATCHERS = [
    (
        name,
        spec["weight"],
        [(kw, *_compile_term(kw)) for kw in spec["keywords"] if _valid_keyword(kw)],
    )
    for name, spec in cfg.KEYWORD_CATEGORIES.items()
]

# 기관 매처: [(canonical, type, [(kind, payload), ...]), ...]
_ORG_MATCHERS = [
    (
        org["canonical"],
        org["type"],
        [_compile_term(t) for t in ([org["canonical"], *org.get("aliases", [])])],
    )
    for org in cfg.ORGANIZATIONS
]


# ── 매칭 ─────────────────────────────────────────────────────────────────────
def _haystack(a: dict) -> str:
    return "\n".join(filter(None, [a.get("title", ""), a.get("summary", ""), a.get("content", "")]))


def _score_article(a: dict) -> None:
    text = _haystack(a)
    text_lower = text.lower()

    score = 0
    matched_keywords: list[str] = []
    matched_categories: list[tuple[str, int]] = []

    for name, weight, terms in _CATEGORY_MATCHERS:
        hit_kw = None
        for kw, kind, payload in terms:
            if _term_matches(kind, payload, text, text_lower):
                hit_kw = kw
                matched_keywords.append(kw)
        if hit_kw is not None:
            score += weight
            matched_categories.append((name, weight))

    # 대표 카테고리 = 가장 가중치 높은 매칭 카테고리 (동점 시 정의 순서)
    category = "Other"
    if matched_categories:
        category = max(matched_categories, key=lambda t: t[1])[0]

    a["score"] = score
    a["highlight_score"] = score  # 하위 호환용 별칭
    a["category"] = category
    a["matched_keywords"] = list(dict.fromkeys(matched_keywords))  # 순서 유지 중복 제거
    a["matched_categories"] = [n for n, _ in matched_categories]


def _extract_orgs(a: dict) -> None:
    text = _haystack(a)
    text_lower = text.lower()
    found: list[dict] = []
    seen: set[str] = set()
    for canonical, otype, matchers in _ORG_MATCHERS:
        if canonical in seen:
            continue
        for kind, payload in matchers:
            if _term_matches(kind, payload, text, text_lower):
                found.append({"name": canonical, "org_type": otype, "role": "subject"})
                seen.add(canonical)
                break
    a["organizations"] = found


# ── 중복 그룹핑 (제목 토큰 자카드 유사도) ─────────────────────────────────────
_TOKEN_SPLIT = re.compile(r"[^0-9a-z가-힣]+")
_JACCARD_THRESHOLD = 0.6


def _title_tokens(title: str) -> set[str]:
    toks = _TOKEN_SPLIT.split(title.lower())
    return {t for t in toks if len(t) > 1}


def _dedup(articles: list[dict]) -> None:
    """제목 유사도로 union-find 그룹핑. dedup_group_id + is_dup 부여.

    그룹 대표 = 그룹 내 최고 score(동점 시 본문 길이). 대표만 is_dup=False.
    """
    n = len(articles)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    tokens = [_title_tokens(a.get("title", "")) for a in articles]
    for i in range(n):
        ti = tokens[i]
        if not ti:
            continue
        for j in range(i + 1, n):
            tj = tokens[j]
            if not tj:
                continue
            inter = len(ti & tj)
            if not inter:
                continue
            jac = inter / len(ti | tj)
            if jac >= _JACCARD_THRESHOLD:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    for gid, idxs in groups.items():
        # 대표 선정
        rep = max(idxs, key=lambda i: (articles[i]["score"], len(articles[i].get("content", ""))))
        for i in idxs:
            articles[i]["dedup_group_id"] = gid
            articles[i]["is_dup"] = (i != rep)


# ── 공개 API ─────────────────────────────────────────────────────────────────
def curate(articles: list[dict]) -> list[dict]:
    """점수화 → 게이트 → 중복 → 하이라이트 선정. 게이트 통과분만 반환(score desc)."""
    for a in articles:
        _score_article(a)
        _extract_orgs(a)
        a["korean_summary"] = a.get("summary", "")  # 호환 필드(번역 없음, 원문 그대로)

    threshold = cfg.SCORE_THRESHOLD
    kept = [a for a in articles if a["score"] >= threshold]
    dropped = len(articles) - len(kept)
    log.info(f"게이트: {len(articles)}건 중 {len(kept)}건 통과 (임계 {threshold}, {dropped}건 제외)")

    kept.sort(key=lambda a: (a["score"], len(a.get("content", ""))), reverse=True)
    _dedup(kept)

    # 하이라이트: 대표(is_dup=False) 중 상위 N
    reps = [a for a in kept if not a.get("is_dup")]
    top_ids = {id(a) for a in reps[: cfg.TOP_HIGHLIGHTS]}
    for a in kept:
        a["is_highlight"] = id(a) in top_ids

    hl_scores = [a["score"] for a in reps[: cfg.TOP_HIGHLIGHTS]]
    log.info(f"하이라이트 {min(len(reps), cfg.TOP_HIGHLIGHTS)}건 선정 (scores: {hl_scores})")
    return kept


def top_organizations(articles: list[dict], n: int) -> list[tuple[str, str, int]]:
    """등장 기관 빈도 집계 → 상위 n개 [(name, type, count)]."""
    counts: dict[str, int] = {}
    types: dict[str, str] = {}
    for a in articles:
        for o in a.get("organizations", []):
            name = o["name"]
            counts[name] = counts.get(name, 0) + 1
            types[name] = o.get("org_type", "other")
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return [(name, types[name], cnt) for name, cnt in ranked]


def category_counts(articles: list[dict]) -> list[tuple[str, int]]:
    """카테고리별 건수(대표 카테고리 기준) → 건수 내림차순."""
    counts: dict[str, int] = {}
    for a in articles:
        cat = a.get("category", "Other")
        counts[cat] = counts.get(cat, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
