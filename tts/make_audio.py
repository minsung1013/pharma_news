"""오늘자(또는 지정일) 다이제스트 → **하나의** 팟캐스트 에피소드(MP3) 생성.

main.py 가 남긴 ``data/digest_<date>.json`` 을 읽어 아래 구성으로 낭독을 이어붙인다.

  [인트로]  "YYYY년 MM월 DD일, 흑염소 바이오 뉴스 브리핑입니다."
  [1부]     상위 하이라이트 상세 요약
  [2부]     오늘의 종합 (빅파마·바이오텍 주요 움직임)
  [3부]     오늘 수집된 전체 기사 한 문장 요약
  [4부]     주요 뉴스 원문 낭독 (한국어는 한국어 / 영어는 영어 보이스)
  [아웃트로]

기사당 파일 1개가 아니라 **하루 1개 에피소드**만 만든다.

실행:
  python -m tts.make_audio                 # 오늘 날짜
  python -m tts.make_audio --date 2026-07-09
"""
import argparse
import json
import logging
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

# 상위 프로젝트 모듈 임포트를 위해 루트 경로 확보
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tts import config, feed          # noqa: E402
from tts.engine import synthesize_segments  # noqa: E402

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S", stream=sys.stdout)
log = logging.getLogger("make_audio")

_DATE_MP3 = re.compile(r"^\d{4}-\d{2}-\d{2}\.mp3$")
_BULLET = re.compile(r"^[\s•\-*·]+", re.MULTILINE)


def _digest_path(date_str: str) -> Path:
    return config.DIGEST_JSON_DIR / f"digest_{date_str}.json"


def _speak(text: str) -> str:
    """낭독용 정리: 불릿 기호·과도한 공백/개행 → 문장 흐름으로."""
    if not text:
        return ""
    text = _BULLET.sub("", text)
    text = text.replace("•", " ")
    text = re.sub(r"\s*\n+\s*", ". ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\.{2,}", ".", text)
    return text.strip()


def _probe_duration(path: Path) -> float | None:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def _build_segments(dg: dict, date_str: str) -> list[tuple[str, str | None]]:
    ko = config.EDGE_VOICE
    en = config.EDGE_VOICE_EN
    y, m, d = date_str.split("-")
    segs: list[tuple[str, str | None]] = []

    # ── 인트로 ──
    segs.append((f"{y}년 {int(m)}월 {int(d)}일, 흑염소 바이오 뉴스 브리핑입니다.", ko))

    # ── 1부: 하이라이트 ──
    highlights = dg.get("highlights") or []
    if highlights:
        segs.append((f"먼저, 오늘의 핵심 하이라이트 {len(highlights)}건입니다.", ko))
        for i, h in enumerate(highlights, 1):
            title = h.get("title_kr") or h.get("title") or ""
            summary = _speak(h.get("summary") or "")
            segs.append((f"{i}번. {title}. {summary}", ko))

    # ── 2부: 종합 ──
    movements = dg.get("movements") or []
    if movements:
        segs.append(("다음은, 오늘의 종합입니다. 빅파마와 바이오텍의 주요 움직임입니다.", ko))
        segs.append((_speak(". ".join(movements)), ko))

    # ── 3부: 전체 기사 한 문장 요약 ──
    summaries = dg.get("summaries") or []
    if summaries:
        segs.append((f"이어서, 오늘 수집된 전체 기사 {len(summaries)}건을 한 문장씩 요약해 드립니다.", ko))
        # 한 세그먼트에 몰아 넣으면 청킹이 알아서 나눔
        joined = ". ".join(_speak(s.get("korean_summary") or s.get("title") or "") for s in summaries)
        segs.append((joined, ko))

    # ── 4부: 주요 뉴스 원문 낭독 ──
    fulltext = dg.get("podcast_fulltext") or []
    if fulltext:
        segs.append((f"마지막으로, 오늘의 주요 뉴스 {len(fulltext)}건을 원문으로 자세히 전해 드립니다.", ko))
        for i, it in enumerate(fulltext, 1):
            lang = it.get("lang", "ko")
            voice = en if lang == "en" else ko
            title = it.get("title") or ""
            body = it.get("body") or ""
            # 각 꼭지 앞에 한국어 안내 (번호), 이후 제목+본문은 해당 언어 보이스
            segs.append((f"주요 뉴스 {i}.", ko))
            segs.append((f"{title}. {body}", voice))

    # ── 아웃트로 ──
    segs.append(("이상 흑염소 바이오 뉴스였습니다. 내일 아침 다시 찾아뵙겠습니다.", ko))
    return segs


def _episode_summary(dg: dict) -> str:
    nh = len(dg.get("highlights") or [])
    ns = len(dg.get("summaries") or [])
    nf = len(dg.get("podcast_fulltext") or [])
    return f"핵심 하이라이트 {nh}건, 전체 요약 {ns}건, 주요 뉴스 원문 {nf}건."


def main() -> None:
    ap = argparse.ArgumentParser(description="흑염소 바이오 뉴스 에피소드 생성")
    ap.add_argument("--date", default=date.today().strftime("%Y-%m-%d"))
    args = ap.parse_args()
    date_str = args.date

    dpath = _digest_path(date_str)
    if not dpath.exists():
        log.error(f"다이제스트 JSON 없음: {dpath} — main.py 를 먼저 실행하세요.")
        sys.exit(1)
    dg = json.loads(dpath.read_text(encoding="utf-8"))

    segments = _build_segments(dg, date_str)
    total_chars = sum(len(t) for t, _ in segments)
    log.info(f"[{date_str}] 세그먼트 {len(segments)}개, 총 {total_chars:,}자 낭독 시작")

    out = config.AUDIO_DIR / f"{date_str}.mp3"
    synthesize_segments(segments, out)
    dur = _probe_duration(out)
    log.info(f"에피소드 생성: {out.name} ({out.stat().st_size/1e6:.1f} MB, "
             f"{(dur or 0)/60:.1f}분)")

    # ── episodes.json 갱신: 하루 1개 에피소드 체계로 정리 ──
    eps = feed.load_episodes()
    # 과거의 '기사당 mp3' 에피소드(날짜.mp3 형식이 아닌 것) 및 같은 날짜 중복 제거
    kept = [e for e in eps if _DATE_MP3.match(e.get("file", "")) and e.get("guid") != date_str]
    kept.append({
        "guid": date_str,
        "url": config.PODCAST_BASE_URL,
        "title": f"{config.PODCAST_TITLE} — {date_str}",
        "file": out.name,
        "bytes": out.stat().st_size,
        "duration_sec": dur,
        "pubDate": format_datetime(
            datetime.strptime(date_str, "%Y-%m-%d").replace(hour=6, tzinfo=timezone.utc)
        ),
        "summary": _episode_summary(dg),
    })

    # 오래된 에피소드 정리 (최근 N일 유지)
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.FEED_RETENTION_DAYS)
    final: list[dict] = []
    for e in kept:
        try:
            old = parsedate_to_datetime(e["pubDate"]) < cutoff
        except Exception:
            old = False
        if old and e.get("file") != out.name:
            (config.AUDIO_DIR / e["file"]).unlink(missing_ok=True)
        else:
            final.append(e)

    feed.save_episodes(final)
    feed.write_feed(final)
    log.info(f"완료: 총 {len(final)}개 에피소드. 피드 → {config.FEED_PATH}")


if __name__ == "__main__":
    main()
