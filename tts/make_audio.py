"""오늘자(또는 지정일) 국내 기사 원문 → TTS MP3 → 팟캐스트 피드 갱신.

실행:
  python -m tts.make_audio                 # 오늘 날짜
  python -m tts.make_audio --date 2026-07-07
  python -m tts.make_audio --limit 5       # 테스트용 소량

메인 디제스트(GitHub Actions)가 커밋한 seen_links.json 을 기준으로,
국내 호스트 + 해당 날짜의 신규 링크만 낭독 대상으로 삼는다.
"""
import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from urllib.parse import urlparse

# 상위 프로젝트 모듈(scraper) 임포트를 위해 루트 경로 확보
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from tts import config, feed, textprep  # noqa: E402
from tts.engine import synthesize        # noqa: E402
from scraper import scrape_article       # noqa: E402

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S", stream=sys.stdout)
log = logging.getLogger("make_audio")


def _korean_links_for(target: str) -> list[str]:
    data = json.loads(config.SEEN_LINKS.read_text(encoding="utf-8"))
    out = []
    for url, seen in data.items():
        if seen != target:
            continue
        if urlparse(url).hostname in config.KOREAN_HOSTS:
            out.append(url)
    return out


def _file_for(url: str, seen: str) -> str:
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    return f"{seen}_{h}.mp3"


def _probe_duration(path) -> float | None:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="국내 기사 TTS 오디오 생성")
    ap.add_argument("--date", default=date.today().strftime("%Y-%m-%d"))
    ap.add_argument("--limit", type=int, default=0, help="0 = 전체")
    args = ap.parse_args()

    links = _korean_links_for(args.date)
    log.info(f"[{args.date}] 국내 신규 링크 {len(links)}건")
    if args.limit:
        links = links[: args.limit]

    eps = feed.load_episodes()
    have = {e["guid"] for e in eps}
    added = 0

    for i, url in enumerate(links, 1):
        if url in have:
            log.info(f"  ({i}/{len(links)}) SKIP 이미 생성됨")
            continue

        art = scrape_article(url, timeout_sec=config.SCRAPE_TIMEOUT_SEC)
        if not art:
            log.warning(f"  ({i}/{len(links)}) 스크래핑 실패 → 건너뜀")
            continue

        text = textprep.clean_for_tts(art["body"])
        if len(text) < config.MIN_BODY_CHARS:
            log.warning(f"  ({i}/{len(links)}) 본문 짧음({len(text)}자) → 건너뜀")
            continue

        fname = _file_for(url, args.date)
        out = config.AUDIO_DIR / fname
        # 제목 끝 매체명 접미사 제거 (" - 바이오타임즈" 등)
        title = re.sub(r"\s*[-|·]\s*[^-|·]{1,20}$", "", art["title"]).strip() or art["title"] or "(제목 없음)"
        log.info(f"  ({i}/{len(links)}) TTS: {title[:50]} ({len(text)}자)")

        # 낭독 스크립트: 제목 먼저 읽고 본문
        synthesize(f"{title}.\n{text}", out)

        eps.append({
            "guid": url,
            "url": url,
            "title": title,
            "file": fname,
            "bytes": out.stat().st_size,
            "duration_sec": _probe_duration(out),
            "pubDate": format_datetime(
                datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            ),
        })
        have.add(url)
        added += 1

    # 오래된 에피소드 정리 (피드·episodes.json 을 최근 N일로 유지)
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.FEED_RETENTION_DAYS)
    kept: list[dict] = []
    for e in eps:
        try:
            old = parsedate_to_datetime(e["pubDate"]) < cutoff
        except Exception:
            old = False
        if old:
            (config.AUDIO_DIR / e["file"]).unlink(missing_ok=True)
        else:
            kept.append(e)
    pruned = len(eps) - len(kept)

    feed.save_episodes(kept)
    feed.write_feed(kept)
    log.info(f"완료: {added}건 신규, {pruned}건 정리, 총 {len(kept)}건. 피드 → {config.FEED_PATH}")


if __name__ == "__main__":
    main()
