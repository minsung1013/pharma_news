import os
from dotenv import load_dotenv

load_dotenv()

NEWS_SOURCES = [
    {"name": "STAT News",            "url": "https://www.statnews.com/feed/",                        "type": "news"},
    {"name": "Fierce Biotech",       "url": "https://www.fiercebiotech.com/rss/xml",                 "type": "news"},
    {"name": "Fierce Pharma",        "url": "https://www.fiercepharma.com/rss/xml",                  "type": "news"},
    {"name": "BioPharma Dive",       "url": "https://www.biopharmadive.com/feeds/news/",              "type": "news"},
    {"name": "Endpoints News",       "url": "https://endpts.com/feed/",                              "type": "news"},
    {"name": "Nature Biotechnology", "url": "https://www.nature.com/nbt.rss",                        "type": "news"},
    {"name": "바이오타임즈",          "url": "https://www.biotimes.co.kr/rss/allArticle.xml",        "type": "news"},
    {"name": "히트뉴스",             "url": "https://www.hitnews.co.kr/rss/allArticle.xml",          "type": "news"},
]

PAPER_SOURCES = [
    {"name": "bioRxiv: Bioinformatics",    "url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=bioinformatics",            "type": "paper"},
    {"name": "bioRxiv: Synthetic Biology", "url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=synthetic_biology",         "type": "paper"},
    {"name": "bioRxiv: Pharmacology",      "url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=pharmacology_and_toxicology", "type": "paper"},
    {"name": "arXiv: q-bio",               "url": "http://export.arxiv.org/rss/q-bio",                                             "type": "paper"},
    {"name": "arXiv: cs.LG",               "url": "http://export.arxiv.org/rss/cs.LG",                                             "type": "paper"},
]

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

MAX_NEWS_PER_SOURCE   = int(os.getenv("MAX_NEWS_PER_SOURCE", "10"))
MAX_PAPERS_PER_SOURCE = int(os.getenv("MAX_PAPERS_PER_SOURCE", "5"))
SCRAPE_TIMEOUT_SEC    = int(os.getenv("SCRAPE_TIMEOUT_SEC", "30"))
ORG_CSV_PATH          = os.getenv("ORG_CSV_PATH", "./data/organizations.csv")
