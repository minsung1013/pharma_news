"""TTS 파이프라인 설정.

메인 디제스트(config.py)와 분리하여 로컬 TTS 관련 값만 관리한다.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── 경로 ──────────────────────────────────────────────────────────────────
DATA_DIR      = Path("data")
AUDIO_DIR     = DATA_DIR / "audio"          # MP3 저장 (gitignore)
EPISODES_JSON = AUDIO_DIR / "episodes.json"  # 에피소드 메타 누적
FEED_PATH     = AUDIO_DIR / "feed.xml"       # 생성된 RSS
SEEN_LINKS    = DATA_DIR / "seen_links.json"
COVER_PATH    = AUDIO_DIR / "cover.png"      # 팟캐스트 커버 아트 (repo 커밋)
# 하루치 다이제스트 JSON (main.py 가 생성 → make_audio 가 소비). 날짜별.
DIGEST_JSON_DIR = DATA_DIR

# ── 국내(한국어) 기사 판별 호스트 ─────────────────────────────────────────
KOREAN_HOSTS = {"www.biotimes.co.kr", "biotimes.co.kr", "www.ibric.org", "ibric.org"}

# ── TTS (edge-tts) ─────────────────────────────────────────────────────────
# 한국어 뉴럴 보이스: ko-KR-SunHiNeural(여) / ko-KR-InJoonNeural(남)
EDGE_VOICE  = os.getenv("EDGE_VOICE", "ko-KR-SunHiNeural")
# 영어 기사 원문 낭독용 보이스 (영어는 영어로)
EDGE_VOICE_EN = os.getenv("EDGE_VOICE_EN", "en-US-AriaNeural")
EDGE_RATE   = os.getenv("EDGE_RATE", "+0%")     # 예: "+10%" 로 빠르게
EDGE_VOLUME = os.getenv("EDGE_VOLUME", "+0%")
# 팟캐스트 낭독 구성 (큐레이션 뉴스 그대로 읽기)
PODCAST_GAP_SEC       = float(os.getenv("PODCAST_GAP_SEC", "1.0"))    # 뉴스 사이 무음 공백(초)
PODCAST_MAX_ITEMS     = int(os.getenv("PODCAST_MAX_ITEMS", "0"))      # 낭독 최대 뉴스 수(0=전체)
PODCAST_MAX_ITEM_CHARS = int(os.getenv("PODCAST_MAX_ITEM_CHARS", "600"))  # 뉴스당 낭독 본문 상한(자)

# ── 팟캐스트 / 호스팅 ──────────────────────────────────────────────────────
# 서버리스(GitHub Releases) 호스팅이 기본. MP3 는 릴리스 애셋으로 올라가고
# enclosure URL 은 그 다운로드 주소를 가리킨다.
#   릴리스 태그 'audio' → https://github.com/<owner>/<repo>/releases/download/audio/<file>
GH_REPO = os.getenv("GITHUB_REPOSITORY", "minsung1013/pharma_news")
RELEASE_TAG = os.getenv("AUDIO_RELEASE_TAG", "audio")

# 오디오 파일 base URL (로컬 서버로 미리보기하려면 http://127.0.0.1:8080/audio 로 오버라이드)
AUDIO_BASE_URL = os.getenv(
    "AUDIO_BASE_URL",
    f"https://github.com/{GH_REPO}/releases/download/{RELEASE_TAG}",
).rstrip("/")

PODCAST_BASE_URL = os.getenv("PODCAST_BASE_URL", f"https://github.com/{GH_REPO}").rstrip("/")
PODCAST_TITLE    = os.getenv("PODCAST_TITLE", "흑염소 바이오 뉴스")
PODCAST_DESC     = os.getenv(
    "PODCAST_DESC",
    "매일 아침 제약·바이오·AI 뉴스를 흑염소가 브리핑합니다. "
    "핵심 하이라이트 요약과 전체 기사 요약, 그리고 주요 뉴스 원문 낭독까지 하나의 에피소드로.",
)
PODCAST_AUTHOR   = os.getenv("PODCAST_AUTHOR", "흑염소 바이오 뉴스")
PODCAST_LANG     = os.getenv("PODCAST_LANG", "ko")
PODCAST_OWNER_EMAIL = os.getenv("PODCAST_OWNER_EMAIL", "podcast@example.com")

# 커버 아트 URL (repo 에 커밋된 cover.png 를 raw 로 서빙)
_GH_BRANCH = os.getenv("GITHUB_REF_NAME", "main")
COVER_URL = os.getenv(
    "PODCAST_COVER_URL",
    f"https://raw.githubusercontent.com/{GH_REPO}/{_GH_BRANCH}/data/audio/cover.png",
)

# 피드에 유지할 최근 일수 (episodes.json 도 이 범위로 정리)
FEED_RETENTION_DAYS = int(os.getenv("FEED_RETENTION_DAYS", "30"))

SERVER_HOST = os.getenv("TTS_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("TTS_SERVER_PORT", "8080"))
