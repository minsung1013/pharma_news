# BioPharma AI News Digest — 개발 스펙

## 프로젝트 개요

글로벌·국내 제약·바이오·AI **뉴스 + 신규 연구 논문**을 매일 1회 RSS로 수집하고,
OpenAI API(또는 교체 가능한 LLM)로 분류·요약 후 Gmail로 발송하는 Python 자동화 스크립트.

사용자 컨텍스트: LG AI연구원 사업 개발팀(BD). 빅파마·바이오텍의 딜·파트너십·기술 동향과 관련 연구 동향 모니터링이 주목적.

- **배포**: 초기 로컬 테스트 → GitHub Actions cron으로 이관 예정
- **비용 목표**: 월 $2 이하 (추후 로컬 LLM(Ollama) 전환 가능)
- **발송 빈도**: 하루 1회

---

## 처리 워크플로우

```
[1] RSS 수집
    - 산업 뉴스 8개 소스 + 논문 N개 소스
    - 각 항목: 제목 / RSS summary / 링크 / 발행일
        ↓
[2] LLM 일괄 분류 호출 (1회)
    입력: 전체 항목의 메타 (제목 + RSS summary)
    출력: 항목별로
      - korean_summary: 한 줄 한국어 요약 (40자 이내)
      - category:       LLM이 부여한 영문 카테고리 라벨
      - is_highlight:   관심 키워드 부합 여부 (의미 기반 판단)
      - matched_keywords
      - dedup_group_id: 동일 사건을 다룬 항목들을 같은 ID로 묶음
      - organizations:  기사/논문의 주체 조직 추출
                        [{name, org_type, role}, ...] (없으면 빈 배열)
        ↓
[3] 조직 정보 CSV 누적 (data/organizations.csv에 append)
    - dedup_group별 1건만 기록 (대표 항목)
    - organizations 비어있으면 스킵
        ↓
[4] 하이라이트 본문 스크래핑 (Playwright Chromium headless)
    - dedup_group별 대표 1건만 스크래핑 (중복 호출 절약)
    - 30초 타임아웃 → 실패 시 RSS summary로 fallback
        ↓
[5] 하이라이트별 상세 요약 LLM 호출 (1건/호출)
    - 분량 제한 없음
    - summary + implication(BD 시사점) 모두 작성
        ↓
[6] 종합 분석 LLM 호출 (1회)
    - 핵심 트렌드 / 빅파마·바이오텍 움직임 / BD 시사점
        ↓
[7] HTML 메일 조립 → Gmail SMTP 발송
```

---

## 기술 스택

- Python 3.10+
- 뉴스 수집: `feedparser`
- 본문 스크래핑: `playwright` (Chromium headless, 하이라이트만)
- LLM: `openai` (기본), Provider 패턴으로 교체 가능
- 이메일: `smtplib` + Gmail SMTP (App Password)
- 환경변수: `python-dotenv`
- 배포: GitHub Actions cron (추후)

---

## 디렉토리 구조

```
biopharma-digest/
├── main.py              # 진입점 — 1회 실행 (수집→분류→CSV→스크래핑→요약→발송)
├── fetcher.py           # RSS 수집
├── scraper.py           # Playwright 본문 스크래핑
├── classifier.py        # LLM 일괄 분류
├── summarizer.py        # LLM 하이라이트/종합 요약 (Provider 패턴)
├── org_logger.py        # 조직 정보 CSV 누적
├── mailer.py            # Gmail HTML 메일 발송
├── config.py            # 소스 목록, 키워드, 설정값
├── data/
│   └── organizations.csv  # BD 잠재 고객 누적 데이터 (append-only)
├── .env                 # 시크릿 (git 제외)
├── .env.example
├── requirements.txt
├── .github/workflows/
│   └── digest.yml       # GitHub Actions cron (추후)
└── README.md
```

---

## 산업 뉴스 소스 (8개)

```python
NEWS_SOURCES = [
    # 영문 (6)
    {"name": "STAT News",            "url": "https://www.statnews.com/feed/",            "type": "news"},
    {"name": "Fierce Biotech",       "url": "https://www.fiercebiotech.com/rss/xml",     "type": "news"},
    {"name": "Fierce Pharma",        "url": "https://www.fiercepharma.com/rss/xml",      "type": "news"},
    {"name": "BioPharma Dive",       "url": "https://www.biopharmadive.com/feeds/news/", "type": "news"},
    {"name": "Endpoints News",       "url": "https://endpts.com/feed/",                  "type": "news"},
    {"name": "Nature Biotechnology", "url": "https://www.nature.com/nbt.rss",            "type": "news"},
    # 국내 (2)
    {"name": "바이오스펙테이터",      "url": "http://www.biospectator.com/rss/allArticle.xml", "type": "news"},
    {"name": "히트뉴스",             "url": "https://www.hitnews.co.kr/rss/allArticle.xml",   "type": "news"},
]
```

> **TODO**: 첫 실행 시 각 RSS URL의 응답 200 + 파싱 가능 여부 확인.
> 특히 바이오스펙테이터는 도메인이 `biospectator.com`인지 검증 (이전 스펙에는 `biotimes.co.kr`로 잘못 표기되어 있었음 — 그쪽은 별개 매체 "바이오타임즈").

- 소스당 최신 기사 최대 **10건**
- 발행일 기준 **24시간 이내** (KST — `TZ=Asia/Seoul` 환경변수로 통일)

---

## 연구 논문 소스 (Preprint + Journal)

```python
PAPER_SOURCES = [
    # bioRxiv (subject별 RSS)
    {"name": "bioRxiv: Bioinformatics",         "url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=bioinformatics",            "type": "paper"},
    {"name": "bioRxiv: Synthetic Biology",      "url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=synthetic_biology",         "type": "paper"},
    {"name": "bioRxiv: Pharmacology",           "url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=pharmacology_and_toxicology", "type": "paper"},
    # arXiv
    {"name": "arXiv: q-bio (Quantitative Bio)", "url": "http://export.arxiv.org/rss/q-bio",                                             "type": "paper"},
    {"name": "arXiv: cs.LG (ML)",               "url": "http://export.arxiv.org/rss/cs.LG",                                             "type": "paper"},
    # PubMed 키워드 검색 RSS — PubMed에서 검색 후 "Create RSS"로 발급
    {"name": "PubMed: AI drug discovery",       "url": "<발급된 PubMed RSS URL>",                                                       "type": "paper"},
]
```

- 소스당 최신 논문 최대 **5건**
- 발행일 24시간 이내
- 논문은 본문 스크래핑 부담이 있어 기본은 **abstract(=RSS summary)** 만 사용. 하이라이트로 선정된 논문은 가능 시 결과/결론 섹션 추가 스크래핑.

---

## 관심 키워드 (하이라이트 필터)

```python
INTEREST_KEYWORDS = [
    # AI 활용
    "artificial intelligence", "AI", "machine learning", "deep learning",
    "AI drug discovery", "AI diagnostics", "foundation model",
    # 항체 설계
    "antibody design", "antibody engineering", "bispecific", "ADC",
    # 단백질 구조 예측·설계
    "protein design", "protein structure", "AlphaFold", "RoseTTAFold",
    "de novo protein", "protein language model",
    # 디지털 병리학
    "digital pathology", "computational pathology", "whole slide image", "WSI",
    # 공간전사체
    "spatial transcriptomics", "spatial omics", "Visium", "Xenium",
    # 사이클로펩타이드
    "cyclic peptide", "macrocycle", "peptide drug",
    # 한국어 키워드
    "항체", "단백질 설계", "디지털 병리", "공간전사체", "사이클로펩타이드",
]
```

키워드 매칭은 LLM 분류 단계에서 **의미 기반**으로 수행 (단순 substring이 아니라, 문맥상 부합 여부를 LLM이 판단).

---

## LLM Provider 패턴

```python
# providers.py
from abc import ABC, abstractmethod
import os

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, json_mode: bool = True) -> str: ...

class OpenAIProvider(LLMProvider):
    def complete(self, system, user, json_mode=True):
        from openai import OpenAI
        client = OpenAI()
        kwargs = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return client.chat.completions.create(**kwargs).choices[0].message.content

class OllamaProvider(LLMProvider):
    def complete(self, system, user, json_mode=True):
        import requests
        payload = {
            "model": os.getenv("OLLAMA_MODEL", "llama3"),
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        res = requests.post(f"{os.getenv('OLLAMA_BASE_URL')}/api/chat", json=payload, timeout=120)
        return res.json()["message"]["content"]

class InternalAPIProvider(LLMProvider):
    def complete(self, system, user, json_mode=True):
        import requests
        headers = {"Authorization": f"Bearer {os.getenv('INTERNAL_API_KEY')}"}
        payload = {"system": system, "user": user, "json_mode": json_mode}
        res = requests.post(os.getenv("INTERNAL_API_URL"), json=payload, headers=headers, timeout=120)
        return res.json()["content"]

def get_provider() -> LLMProvider:
    p = os.getenv("LLM_PROVIDER", "openai")
    return {"openai": OpenAIProvider, "ollama": OllamaProvider, "internal": InternalAPIProvider}[p]()
```

---

## 프롬프트 설계

### Prompt 1 — 일괄 분류 + 한국어 요약 (모든 항목)

전체 항목 메타를 한 번에 LLM에 넣어 분류·요약·중복 그룹핑·하이라이트 판단을 동시에 수행.

```python
CLASSIFY_SYSTEM = """
당신은 글로벌 제약·바이오·AI 산업의 뉴스/논문 큐레이터입니다.
입력으로 오늘 수집된 항목 목록(JSON)이 주어집니다. 각 항목에 대해 다음을 수행하세요.

1. korean_summary: RSS 요약을 기반으로 한국어 한 문장(40자 이내) 요약.
   - 주어 + 행동 중심, 수치·금액 포함, 마침표로 끝낼 것.
2. category: 핵심 주제 라벨을 영문 단답으로 부여.
   예: "Digital Pathology", "Big Pharma Deal", "Antibody Engineering",
       "AI Drug Discovery", "Clinical Trial", "Protein Design",
       "Funding", "Regulation".
3. is_highlight: 아래 관심 키워드 목록과 의미상 부합하면 true (단순 단어 일치가 아닌 문맥 기반 판단).
4. matched_keywords: 부합한 키워드들 (없으면 빈 배열).
5. dedup_group_id: 동일 사건/주제를 다룬 항목들에 같은 정수 ID 부여.
   완전히 다른 주제는 각자 고유 ID. 그룹의 대표는 가장 정보량이 많은 항목.
6. organizations: 기사/논문의 주체 조직을 모두 추출.
   - name: 정식 명칭 (예: "Roche", "PathAI", "MIT Broad Institute")
   - org_type: pharma | biotech | academic | startup | hospital | govt | other
   - role: acquirer | target | partner | investor | author_lab | developer | regulator | subject | other
     (M&A 기사: 인수자=acquirer, 피인수=target.
      파트너십: 양측 모두 partner. 투자 기사: 투자자=investor, 피투자=target.
      논문: 1저자/교신저자 소속=author_lab.
      그 외 기사의 주인공=subject.)
   - 일반 산업 동향 기사처럼 특정 조직이 주체가 아니면 빈 배열.

관심 키워드 목록:
{keywords}

반드시 JSON으로만 응답:
{
  "items": [
    {
      "id": <원본 id>,
      "korean_summary": "...",
      "category": "...",
      "is_highlight": true | false,
      "matched_keywords": ["..."],
      "dedup_group_id": <int>,
      "organizations": [
        {"name": "...", "org_type": "...", "role": "..."}
      ]
    }
  ]
}
"""

CLASSIFY_USER = """
오늘의 항목 목록:
{articles_json}
"""
```

`articles_json` 입력 예시:
```json
[
  {"id": 1, "type": "news",  "source": "STAT News", "title": "...", "summary": "...", "link": "..."},
  {"id": 2, "type": "paper", "source": "bioRxiv",   "title": "...", "summary": "<abstract>", "link": "..."}
]
```

### Prompt 2 — 하이라이트 상세 요약 (스크래핑 본문 기반)

```python
HIGHLIGHT_SYSTEM = """
당신은 LG AI연구원 사업 개발(BD)팀을 위한 제약·바이오·AI 산업 애널리스트입니다.
주어진 본문(또는 논문 abstract)을 한국어로 깊이 있게 요약하고 BD 관점 시사점을 제시하세요.

규칙:
- title_kr: 한국어 제목 (자연스럽게 의역 가능)
- summary: 본문 핵심을 충실히 요약. 분량 제한 없음.
  수치, 거래 구조(선금/마일스톤/지분 등), 임상 단계, 기술적 메커니즘 등
  BD 판단에 유용한 디테일을 포함할 것.
- implication: LG AI연구원 BD 관점의 시사점. 분량 제한 없음.
  - 어떤 기술/플레이어가 부상하는지
  - 협업·라이선싱·M&A 관점의 포인트
  - LG AI연구원의 기존 역량(항체 설계, 단백질 설계, 디지털 병리,
    공간전사체, 사이클로펩타이드, AI 신약개발)과의 접점

반드시 JSON으로만 응답:
{
  "title_kr": "...",
  "summary": "...",
  "implication": "..."
}
"""

HIGHLIGHT_USER = """
원문 제목: {title}
타입: {type}            # news | paper
카테고리: {category}
매칭 키워드: {matched_keywords}
원문 링크: {link}

본문:
{body}
"""
```

### Prompt 3 — 종합 분석

```python
DIGEST_SYSTEM = """
당신은 LG AI연구원 사업 개발(BD)팀을 위한 바이오·제약 산업 애널리스트입니다.
오늘 수집된 항목 전체(제목 + 카테고리 + 한국어 한 줄 요약)를 분석해 한국어로 작성하세요.

1. trend: 오늘의 핵심 트렌드 (2~3문장)
2. movements: 빅파마·바이오텍의 주목할 움직임 (딜·투자·파트너십 중심, 3~5개 bullet)
3. lg_ai_implication: LG AI연구원 BD 관점 시사점 (2~3문장)

반드시 JSON으로만 응답:
{"trend": "...", "movements": ["..."], "lg_ai_implication": "..."}
"""

DIGEST_USER = """
오늘의 항목 목록 (분류 결과):
{items_json}
"""
```

---

## 이메일 출력 형식 (HTML)

```
제목: [BioPharma Digest] 2026-05-09 오늘의 뉴스·논문

━━━━━━━━━━━━━━━━━━━━━━━━
📰 오늘의 뉴스
━━━━━━━━━━━━━━━━━━━━━━━━
[STAT News]
• Roche, PathAI를 최대 $1.05B에 인수 합의. [링크]
• Pfizer, mRNA 항암제 1상 진입. [링크]
...

[Fierce Biotech]
• ...

(섹션별로 소스명 → 한 줄 한국어 요약 list)

━━━━━━━━━━━━━━━━━━━━━━━━
📑 신규 연구 논문
━━━━━━━━━━━━━━━━━━━━━━━━
[bioRxiv: Bioinformatics]
• <한국어 한 줄 요약>. [링크]
...

━━━━━━━━━━━━━━━━━━━━━━━━
🔍 오늘의 종합
━━━━━━━━━━━━━━━━━━━━━━━━
[핵심 트렌드]
...

[빅파마·바이오텍 주요 움직임]
• ...

[LG AI연구원 BD 관점 시사점]
...

━━━━━━━━━━━━━━━━━━━━━━━━
⭐ 관심 키워드 하이라이트
━━━━━━━━━━━━━━━━━━━━━━━━

🏷 Digital Pathology
Roche, AI 디지털 병리 기업 PathAI 최대 $1.05B에 인수
[요약]
Roche가 PathAI를 인수해 디지털 병리 AI를 진단 사업부에 통합한다.
선금 $750M에 마일스톤 $300M 구조...
(분량 제한 없음)

[BD 시사점]
조직병리 슬라이드 자동 분석이 임상·신약 개발 핵심 인프라로 부상...
(분량 제한 없음)

[원문] [관련 보도 N건]

(이하 하이라이트 반복)
```

- 섹션 1·2 (뉴스·논문 전체): Prompt 1의 `korean_summary`를 그대로 사용 — RSS summary 기반 LLM 한국어 한 줄 요약.
- 섹션 3 (종합): Prompt 3 결과.
- 섹션 4 (하이라이트): Prompt 2 결과 (분량 제한 없음).
- `dedup_group`이 묶인 기사는 대표 1건만 본문에 표시하고 "관련 보도 N건" 표기 (각 링크는 펼침 가능하게).

---

## 조직 누적 데이터 (BD 잠재 고객 분석용)

매 실행마다 `data/organizations.csv` 에 신규 행을 append. 추후 pandas/Excel로 분석.

### 스키마

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `date` | str (YYYY-MM-DD) | 수집일 (KST) |
| `organization` | str | 조직명 (LLM이 추출한 정식 명칭 그대로) |
| `org_type` | enum | `pharma` / `biotech` / `academic` / `startup` / `hospital` / `govt` / `other` |
| `role` | enum | `acquirer` / `target` / `partner` / `investor` / `author_lab` / `developer` / `regulator` / `subject` / `other` |
| `category` | str | LLM 분류 라벨 (예: `Digital Pathology`) |
| `content` | str | 한국어 한 줄 요약 (`korean_summary` 그대로) |
| `link` | str | 원문 URL |
| `source` | str | 출처 매체명 (예: `STAT News`, `bioRxiv: Bioinformatics`) |

### 작성 규칙

- **1 row = (기사, 조직) 쌍**: Roche–PathAI 인수 건은 2개 행 (acquirer + target).
- **dedup_group별 1번만 기록**: 같은 사건을 다룬 기사가 여러 매체에서 나와도 대표 기사 1건만 CSV에 반영.
- **append-only, 일자 간 중복 제거 안 함**: 같은 조직의 반복 등장 자체가 BD 시그널.
- `organizations`가 빈 배열인 기사 (특정 주체가 없는 일반 동향)는 CSV 스킵.
- 파일이 없으면 헤더와 함께 생성, 있으면 append (Python `csv` stdlib 사용 — 신규 의존성 불필요).
- 인코딩: UTF-8 with BOM (`utf-8-sig`) — Excel에서 한글 깨지지 않도록.

### 예시 행

```csv
date,organization,org_type,role,category,content,link,source
2026-05-09,Roche,pharma,acquirer,Digital Pathology,"Roche, PathAI 최대 $1.05B에 인수.",https://...,STAT News
2026-05-09,PathAI,startup,target,Digital Pathology,"Roche, PathAI 최대 $1.05B에 인수.",https://...,STAT News
2026-05-09,MIT Broad Institute,academic,author_lab,Protein Design,"단백질 언어모델 신규 아키텍처 발표.",https://...,bioRxiv: Bioinformatics
```

### 추후 분석 예시 (참고용)

- 빈도 Top-N: `df.groupby('organization').size().sort_values(ascending=False)`
- BD 타겟팅: `df[df.org_type.isin(['biotech','startup']) & (df.role == 'developer')]`
- 시계열 모멘텀: 월별 mention 수 추이로 "뜨는 조직" 식별

---

## 환경변수 (.env.example)

```
# LLM Provider 선택: openai | ollama | internal
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Ollama (선택)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# 사내 API (선택)
INTERNAL_API_URL=https://internal-api.lgresearch.ai/v1/chat
INTERNAL_API_KEY=...

# Gmail
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
RECIPIENTS=your@gmail.com  # 콤마 구분 다수 가능

# 타임존 (RSS 24시간 필터 기준)
TZ=Asia/Seoul

# 운영 옵션
MAX_NEWS_PER_SOURCE=10
MAX_PAPERS_PER_SOURCE=5
SCRAPE_TIMEOUT_SEC=30
ORG_CSV_PATH=./data/organizations.csv
```

---

## 실행 방법 (로컬 테스트)

```bash
# 의존성 설치
pip install -r requirements.txt
playwright install chromium  # 첫 1회

# 환경변수 설정
cp .env.example .env
# .env 편집

# 1회 실행 (수집→분류→스크래핑→요약→발송)
python main.py

# 발송 없이 콘솔 미리보기 (메일은 보내지 않음)
python main.py --dry-run
```

---

## requirements.txt

```
feedparser
openai
playwright
python-dotenv
requests
```

---

## 실패 처리 정책

| 단계 | 실패 시 동작 |
|------|--------------|
| RSS fetch | 해당 소스만 스킵, 로그 남기고 계속 진행 |
| LLM 일괄 분류 | 1회 재시도 → 실패 시 종료 (후속 단계 불가) |
| LLM JSON 파싱 실패 | 1회 재시도 → 그래도 실패 시 해당 호출만 스킵 |
| 조직 CSV append | I/O 실패 시 stderr 경고만 남기고 메일 발송은 계속 (CSV는 부수 효과) |
| Playwright 스크래핑 | 30초 타임아웃, 실패 시 RSS summary로 fallback |
| 하이라이트 상세 요약 LLM | 해당 항목만 스킵, 나머지는 계속 |
| 종합 분석 LLM | 해당 섹션만 비우고 메일은 발송 |
| Gmail SMTP | 3회 재시도 (지수 백오프) → 실패 시 비-zero exit (Actions가 실패 알림) |

모든 단계는 stdout에 구조화된 로그를 남겨 GitHub Actions 로그에서 추적 가능.

---

## 비용 추정 (gpt-4o-mini 기준, 가격: in $0.15 / out $0.60 per 1M tokens)

| 호출 | in (토큰) | out (토큰) | 일일 비용 |
|------|-----------|------------|-----------|
| 일괄 분류 (~100항목) | ~25K | ~5K | ~$0.007 |
| 하이라이트 상세 (5~10건) | ~30K | ~10K | ~$0.011 |
| 종합 분석 | ~5K | ~1K | ~$0.001 |
| **합계** | | | **~$0.02/일** |

월 ~$0.6 → **목표 $2 이내 충분**, 논문 추가·하이라이트 증가 여지 포함해도 여유.

---

## GitHub Actions 자동화 (추후)

```yaml
# .github/workflows/digest.yml
name: BioPharma Digest
on:
  schedule:
    - cron: '0 23 * * *'   # UTC 23:00 = KST 08:00
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    env:
      TZ: Asia/Seoul
      LLM_PROVIDER: openai
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
      GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
      RECIPIENTS: ${{ secrets.RECIPIENTS }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: playwright install --with-deps chromium
      - run: python main.py
      # 조직 CSV는 매 실행마다 append되므로 영속화 필요. 옵션:
      #  (a) 같은 레포에 commit-back (간단, 단 git 충돌 주의)
      #  (b) actions/upload-artifact + 다음 run에서 download-artifact
      #  (c) 외부 스토리지(S3, GCS, Google Sheets)에 push
      # 로컬 테스트 단계에서는 단순 파일로 충분.
```

---

## 추후 확장

- `LLM_PROVIDER=ollama` 로 로컬 모델 전환 (API 비용 0)
- 수신자 목록 확장 (팀 전체 배포)
- 키워드/소스 추가는 `config.py`에서
- 일자 간 중복 방지 — 발송 이력 캐시 (SQLite or JSON 파일)
- Slack/Teams 발송 채널 추가
