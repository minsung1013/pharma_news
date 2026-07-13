import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Windows 콘솔 UTF-8 설정 (한국어·특수문자 로그 깨짐 방지)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


_SEEN_LINKS_FILE = Path("data/seen_links.json")


def _load_seen_links() -> set[str]:
    if not _SEEN_LINKS_FILE.exists():
        return set()
    try:
        data = json.loads(_SEEN_LINKS_FILE.read_text(encoding="utf-8"))
        return set(data.keys())
    except Exception:
        return set()


def _save_seen_links(new_links: list[str]) -> None:
    _SEEN_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if _SEEN_LINKS_FILE.exists():
        try:
            data = json.loads(_SEEN_LINKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    today_str = date.today().strftime("%Y-%m-%d")
    for link in new_links:
        if link:
            data[link] = today_str
    # 최근 14일치만 보존
    cutoff = (date.today() - timedelta(days=14)).strftime("%Y-%m-%d")
    data = {k: v for k, v in data.items() if v >= cutoff}
    _SEEN_LINKS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_podcast(articles: list[dict], today: str) -> None:
    """팟캐스트용 다이제스트 JSON 생성.

    큐레이션 통과 뉴스(중복 대표만)를 점수 순서대로 items 로 저장한다.
    make_audio 가 이 items 를 그대로 낭독한다(스크래핑 없음).
    실패해도 뉴스레터를 막지 않도록 예외를 삼킨다.
    """
    try:
        from tts import config as tcfg

        reps = [a for a in articles if not a.get("is_dup")]
        if tcfg.PODCAST_MAX_ITEMS > 0:
            reps = reps[: tcfg.PODCAST_MAX_ITEMS]

        items: list[dict] = []
        for a in reps:
            text = (a.get("summary") or a.get("content") or "").strip()
            text = text[: tcfg.PODCAST_MAX_ITEM_CHARS]
            if not text:
                text = a.get("title", "")
            items.append({
                "title":    a.get("title", ""),
                "text":     text,
                "lang":     a.get("lang", "ko"),
                "source":   a.get("source", ""),
                "category": a.get("category", ""),
                "score":    a.get("score", 0),
                "link":     a.get("link", ""),
            })

        dg = {"date": today, "items": items}
        out = Path(f"data/digest_{today}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dg, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info(f"팟캐스트 데이터 저장 → {out} (뉴스 {len(items)}건)")
    except Exception as e:
        log.warning(f"팟캐스트 데이터 준비 실패(뉴스레터는 계속): {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BioPharma & AI News Digest")
    parser.add_argument("--dry-run", action="store_true", help="메일 발송 없이 HTML 파일로 저장")
    parser.add_argument("--no-podcast", action="store_true", help="팟캐스트 데이터 준비 건너뛰기")
    args = parser.parse_args()

    from config   import NEWS_SOURCES, FETCH_WINDOW_HOURS
    from fetcher  import fetch_all
    from curator  import curate
    from mailer   import build_html, send_mail

    today = date.today().strftime("%Y-%m-%d")

    # ── [1] RSS 수집 ──────────────────────────────────────────────────────────
    log.info("=== [1] RSS 수집 시작 ===")
    articles = fetch_all(NEWS_SOURCES, window_hours=FETCH_WINDOW_HOURS)
    if not articles:
        log.warning("수집된 기사가 없습니다. 종료.")
        return

    seen_links = _load_seen_links()
    before = len(articles)
    articles = [a for a in articles if a.get("link") not in seen_links]
    skipped = before - len(articles)
    if skipped:
        log.info(f"과거 중복 기사 {skipped}건 제외 → 신규 {len(articles)}건")
    if not articles:
        log.warning("신규 기사가 없습니다 (모두 과거 중복). 종료.")
        return
    for i, a in enumerate(articles):
        a["id"] = i

    # ── [2] 규칙 기반 큐레이션 (점수·게이트·중복·하이라이트) ──────────────────
    log.info("=== [2] 큐레이션 ===")
    curated = curate(articles)
    if not curated:
        log.warning("게이트를 통과한 기사가 없습니다. 종료.")
        return

    # ── [3] 팟캐스트 데이터 준비 (무손상 유지) ───────────────────────────────
    if not args.no_podcast:
        log.info("=== [3] 팟캐스트 데이터 준비 ===")
        _prepare_podcast(curated, today)

    # ── [4] 뉴스레터 조립 ─────────────────────────────────────────────────────
    log.info("=== [4] 뉴스레터 조립 ===")
    html = build_html(curated, today)

    if args.dry_run:
        out_path = f"digest_{today}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        log.info(f"Dry-run: HTML saved → {out_path} (seen_links 미저장)")
        return

    _save_seen_links([a.get("link", "") for a in curated])
    log.info(f"Seen links 저장 완료 ({len(curated)}건)")

    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password  = os.environ["GMAIL_APP_PASSWORD"]
    recipients    = [r.strip() for r in os.environ["RECIPIENTS"].split(",") if r.strip()]

    send_mail(html, today, gmail_address, app_password, recipients)
    log.info("=== 완료 ===")


if __name__ == "__main__":
    main()
