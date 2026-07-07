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

# ── 국내(한국어) 기사 판별 호스트 ─────────────────────────────────────────
KOREAN_HOSTS = {"www.biotimes.co.kr", "biotimes.co.kr", "www.ibric.org", "ibric.org"}

# ── TTS (edge-tts) ─────────────────────────────────────────────────────────
# 한국어 뉴럴 보이스: ko-KR-SunHiNeural(여) / ko-KR-InJoonNeural(남)
EDGE_VOICE  = os.getenv("EDGE_VOICE", "ko-KR-SunHiNeural")
EDGE_RATE   = os.getenv("EDGE_RATE", "+0%")     # 예: "+10%" 로 빠르게
EDGE_VOLUME = os.getenv("EDGE_VOLUME", "+0%")
MIN_BODY_CHARS = int(os.getenv("TTS_MIN_BODY_CHARS", "200"))
SCRAPE_TIMEOUT_SEC = int(os.getenv("SCRAPE_TIMEOUT_SEC", "30"))

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
PODCAST_TITLE    = os.getenv("PODCAST_TITLE", "국내 바이오·제약 뉴스 낭독")
PODCAST_DESC     = os.getenv("PODCAST_DESC", "매일 수집한 국내 기사 원문을 edge-tts로 낭독한 오디오")
PODCAST_AUTHOR   = os.getenv("PODCAST_AUTHOR", "pharma_news")
PODCAST_LANG     = os.getenv("PODCAST_LANG", "ko")

# 피드에 유지할 최근 일수 (episodes.json 도 이 범위로 정리)
FEED_RETENTION_DAYS = int(os.getenv("FEED_RETENTION_DAYS", "30"))

SERVER_HOST = os.getenv("TTS_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("TTS_SERVER_PORT", "8080"))
