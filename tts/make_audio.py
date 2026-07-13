"""오늘자(또는 지정일) 큐레이션 뉴스 → **하나의** 팟캐스트 에피소드(MP3).

main.py 가 남긴 ``data/digest_<date>.json`` 의 items(큐레이션 통과 뉴스)를
점수 순서대로 낭독한다.

  [인트로]
  각 뉴스마다:
    [무음 공백] → [전환 멘트(한국어)] → [제목 + 요약]
                 한국어 기사는 한국어 보이스, 영어 기사는 영어 보이스로 낭독.
  [아웃트로]

뉴스 사이에 충분한 공백과 전환 멘트를 넣어 듣기 쉽게 구성한다.

실행:
  python -m tts.make_audio                 # 오늘 날짜
  python -m tts.make_audio --date 2026-07-13
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tts import config, feed          # noqa: E402
from tts.engine import synthesize_program  # noqa: E402

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S", stream=sys.stdout)
log = logging.getLogger("make_audio")

_DATE_MP3 = re.compile(r"^\d{4}-\d{2}-\d{2}\.mp3$")
_WS = re.compile(r"\s+")


def _digest_path(date_str: str) -> Path:
    return config.DIGEST_JSON_DIR / f"digest_{date_str}.json"


def _speak(text: str) -> str:
    """낭독용 정리: 과도한 공백/개행 정돈, 불릿 기호 제거."""
    if not text:
        return ""
    text = text.replace("•", " ").replace("·", " ")
    text = _WS.sub(" ", text)
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


def _build_program(dg: dict, date_str: str) -> list[tuple]:
    ko = config.EDGE_VOICE
    en = config.EDGE_VOICE_EN
    gap = config.PODCAST_GAP_SEC
    y, m, d = date_str.split("-")

    items = dg.get("items") or []
    program: list[tuple] = []

    # ── 인트로 ──
    program.append(("say",
        f"{y}년 {int(m)}월 {int(d)}일, 흑염소 바이오 뉴스 브리핑입니다. "
        f"오늘 선별된 뉴스 {len(items)}건을 전해 드립니다.", ko))
    program.append(("gap", gap * 1.5))

    prev_lang = None
    for i, it in enumerate(items, 1):
        lang = it.get("lang", "ko")
        voice = en if lang == "en" else ko
        title = _speak(it.get("title", ""))
        body = _speak(it.get("text", ""))

        # ── 전환 멘트(한국어 호스트) ── 언어가 바뀌면 안내를 붙여 이해를 돕는다.
        if lang == "en":
            cue = "다음은 영어 기사입니다." if prev_lang != "en" else "다음 영어 소식입니다."
        else:
            cue = f"{i}번째 소식입니다."
        program.append(("gap", gap))
        program.append(("say", cue, ko))

        # ── 제목 + 요약 (해당 언어 보이스) ──
        spoken = f"{title}. {body}" if body else title
        program.append(("say", spoken, voice))
        prev_lang = lang

    # ── 아웃트로 ──
    program.append(("gap", gap * 1.5))
    program.append(("say", "이상 흑염소 바이오 뉴스였습니다. 내일 다시 찾아뵙겠습니다.", ko))
    return program


def _episode_summary(dg: dict) -> str:
    items = dg.get("items") or []
    ko = sum(1 for it in items if it.get("lang") != "en")
    en = len(items) - ko
    return f"오늘 선별 뉴스 {len(items)}건 (국내 {ko} · 해외 {en})."


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

    program = _build_program(dg, date_str)
    n_say = sum(1 for p in program if p[0] == "say")
    log.info(f"[{date_str}] 낭독 세그먼트 {n_say}개 합성 시작")

    out = config.AUDIO_DIR / f"{date_str}.mp3"
    synthesize_program(program, out)
    dur = _probe_duration(out)
    log.info(f"에피소드 생성: {out.name} ({out.stat().st_size/1e6:.1f} MB, {(dur or 0)/60:.1f}분)")

    # ── episodes.json 갱신 (하루 1개 에피소드) ──
    eps = feed.load_episodes()
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
