import logging
from typing import Optional

log = logging.getLogger(__name__)

_SELECTORS = [
    "#article-view-content-div",   # BioTimes 등 국내 '뉴스ML' CMS 본문
    "#articleBody",                # 일부 국내 언론 CMS
    "article",
    '[role="main"]',
    "main",
    ".article-body",
    ".article-content",
    ".post-body",
    ".post-content",
    ".entry-content",
    ".story-body",
    "#article-body",
    "#main-content",
]

_MAX_BODY_CHARS = 8_000


def scrape_body(url: str, timeout_sec: int = 30) -> Optional[str]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_extra_http_headers({
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                })
                try:
                    page.goto(url, timeout=timeout_sec * 1000, wait_until="domcontentloaded")
                except PWTimeout:
                    log.warning(f"Timeout ({timeout_sec}s) loading: {url}")
                    return None

                text: Optional[str] = None
                for sel in _SELECTORS:
                    el = page.query_selector(sel)
                    if el:
                        t = el.inner_text()
                        if len(t) > 300:
                            text = t
                            break

                if not text:
                    text = page.inner_text("body")

                return text[:_MAX_BODY_CHARS] if text else None
            finally:
                browser.close()

    except Exception as e:
        log.warning(f"Scrape failed [{url}]: {e}")
        return None


def scrape_article(url: str, timeout_sec: int = 30) -> Optional[dict]:
    """제목 + 본문을 함께 반환 (TTS 낭독용).

    반환: {"title": str, "body": str} 또는 None
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_extra_http_headers({
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                })
                try:
                    page.goto(url, timeout=timeout_sec * 1000, wait_until="domcontentloaded")
                except PWTimeout:
                    log.warning(f"Timeout ({timeout_sec}s) loading: {url}")
                    return None

                # 제목: og:title 우선, 없으면 <title>
                title: Optional[str] = None
                og = page.query_selector('meta[property="og:title"]')
                if og:
                    title = og.get_attribute("content")
                if not title:
                    title = page.title()
                title = (title or "").strip()

                body: Optional[str] = None
                for sel in _SELECTORS:
                    el = page.query_selector(sel)
                    if el:
                        t = el.inner_text()
                        if len(t) > 300:
                            body = t
                            break
                if not body:
                    body = page.inner_text("body")

                if not body:
                    return None
                return {"title": title, "body": body[:_MAX_BODY_CHARS]}
            finally:
                browser.close()

    except Exception as e:
        log.warning(f"Scrape failed [{url}]: {e}")
        return None
