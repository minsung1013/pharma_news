"""뉴스레터 설정 — 소스 · 키워드 카테고리(가중치) · 기관 gazetteer.

LLM 제거 후 모든 큐레이션은 여기 정의된 규칙으로만 수행한다 (curator.py).
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ── 뉴스 소스 (논문 피드 없음) ────────────────────────────────────────────────
NEWS_SOURCES = [
    # 해외 바이오·제약
    {"name": "STAT News",        "url": "https://www.statnews.com/feed/",                                   "lang": "en"},
    {"name": "Fierce Biotech",   "url": "https://www.fiercebiotech.com/rss/xml",                            "lang": "en"},
    {"name": "Fierce Pharma",    "url": "https://www.fiercepharma.com/rss/xml",                             "lang": "en"},
    {"name": "BioPharma Dive",   "url": "https://www.biopharmadive.com/feeds/news/",                        "lang": "en"},
    {"name": "Science News",     "url": "https://www.science.org/rss/news_current.xml",                     "lang": "en"},
    {"name": "ScienceDaily",     "url": "https://www.sciencedaily.com/rss/top/health.xml",                  "lang": "en"},
    # 해외 AI
    {"name": "TechCrunch AI",    "url": "https://techcrunch.com/category/artificial-intelligence/feed/",    "lang": "en"},
    {"name": "VentureBeat AI",   "url": "https://venturebeat.com/category/ai/feed/",                        "lang": "en"},
    {"name": "MIT Tech Review",  "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "lang": "en"},
    {"name": "Ars Technica AI",  "url": "https://arstechnica.com/ai/feed/",                                 "lang": "en"},
    {"name": "The Decoder",      "url": "https://the-decoder.com/feed/",                                    "lang": "en"},
    {"name": "MarkTechPost",     "url": "https://www.marktechpost.com/feed/",                               "lang": "en"},
    {"name": "Google AI Blog",   "url": "https://blog.google/technology/ai/rss/",                           "lang": "en"},
    # 국내 바이오·제약
    {"name": "바이오타임즈",       "url": "https://www.biotimes.co.kr/rss/allArticle.xml",                    "lang": "ko"},
    {"name": "BRIC",             "url": "https://www.ibric.org/bric/rss/bio-news.do",                       "lang": "ko"},
    {"name": "히트뉴스",          "url": "https://www.hitnews.co.kr/rss/allArticle.xml",                     "lang": "ko"},
    {"name": "팜뉴스",           "url": "https://www.pharmnews.com/rss/allArticle.xml",                     "lang": "ko"},
    {"name": "청년의사",          "url": "https://www.docdocdoc.co.kr/rss/allArticle.xml",                   "lang": "ko"},
    # 국내 AI·기술
    {"name": "GeekNews",         "url": "https://news.hada.io/rss/news",                                    "lang": "ko"},
    {"name": "AI타임스",         "url": "https://www.aitimes.com/rss/allArticle.xml",                       "lang": "ko"},
]

# ── 키워드 카테고리 ───────────────────────────────────────────────────────────
# 각 카테고리: label(표시명), weight(매칭 시 가산점), keywords(매칭 대상).
# 한 카테고리는 아무 키워드나 1개 이상 매칭되면 weight 만큼 1회 가산(중복 가산 없음).
# 대소문자/단어경계 처리는 curator._compile_matchers 가 자동 판단한다.
#   - CORE  = 5 : 핵심 관심 분야
#   - EXT   = 3 : 인접 확장 분야
#   - INDUSTRY = 2 : AI 산업 일반(저가중)
_W_CORE = 5
_W_EXT = 3
_W_INDUSTRY = 3

KEYWORD_CATEGORIES: dict[str, dict] = {
    "Digital Pathology": {"weight": _W_CORE, "keywords": [
        "digital pathology", "computational pathology", "whole slide image", "WSI",
        "slide image analysis", "histopathology AI", "디지털 병리", "병리 AI", "전산 병리",
    ]},
    "Pathology Foundation Model": {"weight": _W_CORE, "keywords": [
        "pathology foundation model", "histopathology foundation model",
        "UNI", "Virchow", "CONCH", "Prov-GigaPath", "GigaPath", "PLIP", "TITAN",
        "병리 파운데이션 모델", "병리 기반 모델",
    ]},
    "Spatial Transcriptomics": {"weight": _W_CORE, "keywords": [
        "spatial transcriptomics", "spatial omics", "spatial biology",
        "Visium", "Xenium", "MERFISH", "CosMx", "single-cell spatial",
        "공간전사체", "공간 전사체", "공간 오믹스",
    ]},
    "Oncology": {"weight": _W_CORE, "keywords": [
        "cancer", "oncology", "tumor", "tumour", "carcinoma", "metastasis",
        "immuno-oncology", "immunotherapy", "checkpoint inhibitor", "CAR-T", "neoantigen",
        # 한국어: 1글자 '암'은 '암호화' 등 오탐 → 구체어만 사용
        "종양", "항암", "면역항암", "발암", "암세포", "암 치료", "암 진단",
        "유방암", "폐암", "간암", "위암", "대장암", "췌장암", "전립선암",
        "백혈병", "혈액암", "흑색종",
    ]},
    "Big Pharma": {"weight": _W_CORE, "keywords": [
        "acquisition", "acquires", "to acquire", "merger", "buyout",
        "licensing deal", "partnership", "collaboration", "M&A",
        "인수", "합병", "기술이전", "라이선스", "제휴",
    ]},
    "Antibody Engineering": {"weight": _W_CORE, "keywords": [
        "antibody design", "antibody engineering", "bispecific", "multispecific",
        "ADC", "antibody-drug conjugate", "nanobody", "VHH", "single-domain antibody",
        "Fc engineering", "항체 설계", "이중항체", "항체약물접합체",
    ]},
    "Protein Structure Prediction": {"weight": _W_CORE, "keywords": [
        "protein structure prediction", "AlphaFold", "AlphaFold3", "ESMFold",
        "RoseTTAFold", "OpenFold", "Boltz", "structure prediction", "단백질 구조 예측",
    ]},
    "Protein Design": {"weight": _W_CORE, "keywords": [
        "protein design", "de novo protein", "protein engineering", "RFdiffusion",
        "ProteinMPNN", "protein language model", "generative protein", "binder design",
        "enzyme design", "단백질 설계", "단백질 디자인", "드 노보",
    ]},
    "Alzheimer": {"weight": _W_CORE, "keywords": [
        "Alzheimer", "Alzheimer's", "amyloid", "amyloid-beta", "tau protein",
        "neurodegeneration", "neurodegenerative", "dementia",
        "lecanemab", "donanemab", "Leqembi", "BACE",
        "알츠하이머", "치매", "아밀로이드", "타우", "신경퇴행",
    ]},
    "AI Autonomous Lab": {"weight": _W_CORE, "keywords": [
        "self-driving lab", "self-driving laboratory", "autonomous lab",
        "autonomous laboratory", "automated laboratory", "lab automation",
        "robotic lab", "AI scientist", "cloud lab", "closed-loop experimentation",
        "자율실험실", "실험 자동화", "AI 과학자",
    ]},
    # ── 인접 확장 ──
    "AI Drug Discovery": {"weight": _W_EXT, "keywords": [
        "AI drug discovery", "AI drug design", "generative chemistry",
        "molecular generation", "de novo drug", "virtual screening",
        "AI 신약", "인공지능 신약",
    ]},
    "Single-Cell": {"weight": _W_EXT, "keywords": [
        "single-cell", "single cell", "scRNA-seq", "single-cell RNA",
        "cell atlas", "단일세포", "단일세포 분석",
    ]},
    "Gene/Cell Therapy": {"weight": _W_EXT, "keywords": [
        "gene therapy", "cell therapy", "CRISPR", "base editing", "prime editing",
        "gene editing", "mRNA therapeutic", "유전자치료", "세포치료", "유전자편집",
    ]},
    "Bio Foundation Model": {"weight": _W_EXT, "keywords": [
        "biomedical foundation model", "biological foundation model",
        "genomics language model", "DNA language model", "single-cell foundation model",
        "scGPT", "Evo", "바이오 파운데이션 모델",
    ]},
    "Clinical/Regulatory": {"weight": _W_EXT, "keywords": [
        "clinical trial", "phase 1", "phase 2", "phase 3", "phase I", "phase II", "phase III",
        "FDA approval", "FDA clearance", "EMA", "IND",
        "임상시험", "임상 1상", "임상 2상", "임상 3상", "식약처", "허가",
    ]},
    # ── AI 산업 일반 ──
    "AI Industry": {"weight": _W_INDUSTRY, "keywords": [
        "OpenAI", "Anthropic", "Nvidia", "DeepMind", "Google DeepMind",
        "large language model", "LLM", "GPT", "generative AI", "AI chip",
        "AI funding", "AI agent", "agentic",
        "인공지능", "생성형 AI", "생성형", "거대언어모델", "초거대 AI",
        "AI 에이전트", "파운데이션 모델", "온디바이스 AI", "멀티모달",
    ]},
}

# ── 기관 gazetteer (규칙 기반 조직 추출용) ────────────────────────────────────
# {canonical, type, aliases}. 별칭·정식명이 텍스트에 등장하면 canonical 로 집계.
ORGANIZATIONS: list[dict] = [
    # 빅파마
    {"canonical": "Roche", "type": "pharma", "aliases": ["Genentech", "로슈", "제넨텍"]},
    {"canonical": "Pfizer", "type": "pharma", "aliases": ["화이자"]},
    {"canonical": "Novartis", "type": "pharma", "aliases": ["노바티스"]},
    {"canonical": "Merck", "type": "pharma", "aliases": ["MSD", "머크"]},
    {"canonical": "AstraZeneca", "type": "pharma", "aliases": ["아스트라제네카"]},
    {"canonical": "Johnson & Johnson", "type": "pharma", "aliases": ["J&J", "Janssen", "존슨앤드존슨", "얀센"]},
    {"canonical": "Eli Lilly", "type": "pharma", "aliases": ["Lilly", "일라이릴리", "릴리"]},
    {"canonical": "GSK", "type": "pharma", "aliases": ["GlaxoSmithKline", "글락소스미스클라인"]},
    {"canonical": "Sanofi", "type": "pharma", "aliases": ["사노피"]},
    {"canonical": "AbbVie", "type": "pharma", "aliases": ["애브비"]},
    {"canonical": "Bristol Myers Squibb", "type": "pharma", "aliases": ["BMS", "브리스톨"]},
    {"canonical": "Novo Nordisk", "type": "pharma", "aliases": ["노보노디스크", "노보 노디스크"]},
    {"canonical": "Amgen", "type": "pharma", "aliases": ["암젠"]},
    {"canonical": "Gilead", "type": "pharma", "aliases": ["길리어드"]},
    {"canonical": "Bayer", "type": "pharma", "aliases": ["바이엘"]},
    {"canonical": "Takeda", "type": "pharma", "aliases": ["다케다", "타케다"]},
    {"canonical": "Boehringer Ingelheim", "type": "pharma", "aliases": ["Boehringer", "베링거인겔하임"]},
    {"canonical": "Moderna", "type": "pharma", "aliases": ["모더나"]},
    {"canonical": "Regeneron", "type": "pharma", "aliases": ["리제네론"]},
    {"canonical": "Vertex", "type": "pharma", "aliases": ["버텍스"]},
    {"canonical": "Bristol", "type": "pharma", "aliases": []},
    # AI·테크
    {"canonical": "OpenAI", "type": "ai", "aliases": ["오픈AI", "오픈에이아이"]},
    {"canonical": "Anthropic", "type": "ai", "aliases": ["앤트로픽"]},
    {"canonical": "Google DeepMind", "type": "ai", "aliases": ["DeepMind", "딥마인드"]},
    {"canonical": "Google", "type": "ai", "aliases": ["구글", "Alphabet"]},
    {"canonical": "Microsoft", "type": "ai", "aliases": ["마이크로소프트", "MSFT"]},
    {"canonical": "Meta", "type": "ai", "aliases": ["메타", "Meta AI"]},
    {"canonical": "Nvidia", "type": "ai", "aliases": ["엔비디아"]},
    {"canonical": "Amazon", "type": "ai", "aliases": ["아마존", "AWS"]},
    {"canonical": "Apple", "type": "ai", "aliases": ["애플"]},
    {"canonical": "Hugging Face", "type": "ai", "aliases": ["HuggingFace", "허깅페이스"]},
    {"canonical": "Mistral AI", "type": "ai", "aliases": ["Mistral", "미스트랄"]},
    {"canonical": "xAI", "type": "ai", "aliases": []},
    {"canonical": "Cohere", "type": "ai", "aliases": []},
    # AI×바이오 / 신약 AI
    {"canonical": "Isomorphic Labs", "type": "biotech", "aliases": ["Isomorphic", "아이소모픽"]},
    {"canonical": "Recursion", "type": "biotech", "aliases": ["Recursion Pharmaceuticals"]},
    {"canonical": "Insilico Medicine", "type": "biotech", "aliases": ["Insilico", "인실리코"]},
    {"canonical": "Xaira Therapeutics", "type": "biotech", "aliases": ["Xaira"]},
    {"canonical": "Generate Biomedicines", "type": "biotech", "aliases": ["Generate:Biomedicines"]},
    {"canonical": "EvolutionaryScale", "type": "biotech", "aliases": ["ESM"]},
    {"canonical": "Profluent", "type": "biotech", "aliases": []},
    {"canonical": "Chai Discovery", "type": "biotech", "aliases": ["Chai"]},
    {"canonical": "Iambic Therapeutics", "type": "biotech", "aliases": ["Iambic"]},
    {"canonical": "Cradle", "type": "biotech", "aliases": []},
    {"canonical": "Absci", "type": "biotech", "aliases": []},
    {"canonical": "Cellarity", "type": "biotech", "aliases": []},
    {"canonical": "Genesis Therapeutics", "type": "biotech", "aliases": []},
    # 디지털 병리
    {"canonical": "PathAI", "type": "biotech", "aliases": []},
    {"canonical": "Paige", "type": "biotech", "aliases": ["Paige.AI"]},
    {"canonical": "Lunit", "type": "biotech", "aliases": ["루닛"]},
    {"canonical": "Vuno", "type": "biotech", "aliases": ["뷰노"]},
    {"canonical": "Tempus", "type": "biotech", "aliases": []},
    # 연구기관
    {"canonical": "MIT", "type": "academic", "aliases": ["Massachusetts Institute of Technology"]},
    {"canonical": "Stanford", "type": "academic", "aliases": ["Stanford University", "스탠퍼드"]},
    {"canonical": "Harvard", "type": "academic", "aliases": ["Harvard University", "하버드"]},
    {"canonical": "Broad Institute", "type": "academic", "aliases": ["Broad"]},
    {"canonical": "Baker Lab", "type": "academic", "aliases": ["Institute for Protein Design", "IPD"]},
    {"canonical": "EMBL-EBI", "type": "academic", "aliases": ["EBI"]},
    {"canonical": "NIH", "type": "govt", "aliases": ["National Institutes of Health"]},
    {"canonical": "FDA", "type": "govt", "aliases": ["Food and Drug Administration", "식약처", "식품의약품안전처"]},
    # 국내 바이오·AI
    {"canonical": "LG AI Research", "type": "ai", "aliases": ["LG AI연구원", "엑사원", "EXAONE"]},
    {"canonical": "Samsung Biologics", "type": "pharma", "aliases": ["삼성바이오로직스"]},
    {"canonical": "Celltrion", "type": "pharma", "aliases": ["셀트리온"]},
    {"canonical": "SK bioscience", "type": "pharma", "aliases": ["SK바이오사이언스"]},
    {"canonical": "Yuhan", "type": "pharma", "aliases": ["유한양행"]},
    {"canonical": "Hanmi", "type": "pharma", "aliases": ["한미약품", "한미"]},
    {"canonical": "Daewoong", "type": "pharma", "aliases": ["대웅제약", "대웅"]},
    {"canonical": "HLB", "type": "biotech", "aliases": ["에이치엘비"]},
    {"canonical": "Standigm", "type": "biotech", "aliases": ["스탠다임"]},
    {"canonical": "Deargen", "type": "biotech", "aliases": ["디어젠"]},
    {"canonical": "Naver", "type": "ai", "aliases": ["네이버", "NAVER"]},
    {"canonical": "Kakao", "type": "ai", "aliases": ["카카오"]},
]

# ── 큐레이션 파라미터 (env 로 튜닝) ────────────────────────────────────────────
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "3"))   # 이 미만 점수는 drop
TOP_HIGHLIGHTS  = int(os.getenv("TOP_HIGHLIGHTS", "6"))     # 하이라이트 개수
TOP_ORGS        = int(os.getenv("TOP_ORGS", "8"))          # 통계 '주요 등장 기관' 개수

# 표시 텍스트 길이 상한(자). 초과 기사는 해당 섹션에서 제외.
MAX_HL_CHARS    = int(os.getenv("MAX_HL_CHARS", "4000"))    # 하이라이트(본문)
MAX_NEWS_CHARS  = int(os.getenv("MAX_NEWS_CHARS", "1000"))  # 뉴스(요약)

# 수집 시간창(시간). 이 안에 발행된 기사만 수집.
FETCH_WINDOW_HOURS = int(os.getenv("FETCH_WINDOW_HOURS", "24"))
