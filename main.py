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


def _dedup_representatives(articles: list[dict], highlights_only: bool = False) -> list[dict]:
    """Return one representative per dedup_group_id (first encountered)."""
    seen: set[int] = set()
    reps: list[dict] = []
    for a in articles:
        if highlights_only and not a.get("is_highlight"):
            continue
        gid = a.get("dedup_group_id", a["id"])
        if gid not in seen:
            seen.add(gid)
            reps.append(a)
    return reps


def main() -> None:
    parser = argparse.ArgumentParser(description="BioPharma AI News Digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="메일 발송 없이 HTML 파일로 저장",
    )
    args = parser.parse_args()

    from config import (
        NEWS_SOURCES, PAPER_SOURCES,
        SCRAPE_TIMEOUT_SEC, ORG_CSV_PATH,
    )
    from fetcher             import fetch_all
    from classifier          import classify
    from org_logger          import append_organizations
    from scraper             import scrape_body
    from summarizer          import summarize_highlight, generate_digest
    from mailer              import build_html, send_mail
    from providers           import get_provider, get_bd_provider

    today = date.today().strftime("%Y-%m-%d")

    # ── [1] RSS 수집 ──────────────────────────────────────────────────────────
    log.info("=== [1] RSS 수집 시작 ===")
    articles = fetch_all(NEWS_SOURCES, PAPER_SOURCES)
    if not articles:
        log.warning("수집된 기사가 없습니다. 종료.")
        return

    seen_links = _load_seen_links()
    before = len(articles)
    articles = [a for a in articles if a.get("link") not in seen_links]
    skipped = before - len(articles)
    if skipped:
        log.info(f"과거 중복 기사 {skipped}건 제외 → 신규 {len(articles)}건 처리")
    if not articles:
        log.warning("신규 기사가 없습니다 (모두 과거 중복). 종료.")
        return
    # 필터 후 ID 재부여
    for i, a in enumerate(articles):
        a["id"] = i

    # ── [2] LLM 일괄 분류 ─────────────────────────────────────────────────────
    log.info("=== [2] LLM 분류 시작 ===")
    provider    = get_provider()    # gpt-4o-mini: 분류·번역
    bd_provider = get_bd_provider() # gpt-5.4: 하이라이트 요약·종합 트렌드 분석
    articles = classify(articles, provider)

    # ── [3] 조직 CSV 누적 ─────────────────────────────────────────────────────
    log.info("=== [3] 조직 CSV 기록 ===")
    append_organizations(articles, ORG_CSV_PATH)

    # ── [4] 하이라이트 본문 스크래핑 ──────────────────────────────────────────
    log.info("=== [4] 하이라이트 스크래핑 ===")
    highlight_reps = _dedup_representatives(articles, highlights_only=True)
    log.info(f"Highlights to scrape: {len(highlight_reps)}")

    for h in highlight_reps:
        body = scrape_body(h["link"], timeout_sec=SCRAPE_TIMEOUT_SEC)
        if body:
            log.info(f"  OK  [{h['title'][:60]}]")
        else:
            log.info(f"  FB  [{h['title'][:60]}]  (fallback to RSS summary)")
        h["_body"] = body or h.get("summary", "")

    # ── [5] 하이라이트 상세 요약 ──────────────────────────────────────────────
    log.info("=== [5] 하이라이트 LLM 요약 ===")
    for h in highlight_reps:
        h["_detail"] = summarize_highlight(h, h["_body"], bd_provider)

    # ── [6] 종합 분석 ─────────────────────────────────────────────────────────
    log.info("=== [6] 종합 분석 ===")
    digest = generate_digest(articles, bd_provider)

    # ── [7] 메일 조립 & 발송 ─────────────────────────────────────────────────
    log.info("=== [7] 메일 조립 ===")
    html = build_html(articles, highlight_reps, digest, today)

    _save_seen_links([a.get("link", "") for a in articles])
    log.info(f"Seen links 저장 완료 ({len(articles)}건)")

    if args.dry_run:
        out_path = f"digest_{today}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        log.info(f"Dry-run: HTML saved → {out_path}")
        return

    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password  = os.environ["GMAIL_APP_PASSWORD"]
    recipients    = [r.strip() for r in os.environ["RECIPIENTS"].split(",") if r.strip()]

    send_mail(html, today, gmail_address, app_password, recipients)
    log.info("=== 완료 ===")


if __name__ == "__main__":
    main()
