import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser

log = logging.getLogger(__name__)

_HTML_TAG   = re.compile(r'<[^>]+>')
_WHITESPACE = re.compile(r'\s+')

_SUMMARY_MAX = 2_000    # 매칭·표시용 요약 상한
_CONTENT_MAX = 30_000   # content:encoded(전체 본문) 저장 상한


def _strip_html(text: str) -> str:
    return _WHITESPACE.sub(' ', _HTML_TAG.sub(' ', text)).strip()


def _parse_published(entry) -> Optional[datetime]:
    for attr in ('published_parsed', 'updated_parsed'):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_content(entry) -> str:
    """content:encoded(전체 본문)가 있으면 우선 사용. 없으면 빈 문자열."""
    content_list = getattr(entry, 'content', None)
    if content_list:
        # feedparser: entry.content = [{'value': '...'}, ...]
        raw = " ".join(c.get('value', '') for c in content_list if c.get('value'))
        return _strip_html(raw)[:_CONTENT_MAX]
    return ""


def fetch_source(source: dict, window_hours: int = 24) -> list[dict]:
    try:
        feed = feedparser.parse(
            source["url"],
            agent="Mozilla/5.0 BioPharmaDigest/1.0",
        )
    except Exception as e:
        log.warning(f"[{source['name']}] fetch error: {e}")
        return []

    if feed.bozo and not feed.entries:
        log.warning(f"[{source['name']}] bozo feed (no entries): {feed.bozo_exception}")
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
    items = []

    for entry in feed.entries:
        published = _parse_published(entry)

        if published and published < cutoff:
            continue

        title = _strip_html(getattr(entry, 'title', '') or '').strip()
        if not title:
            continue

        raw_summary = (
            getattr(entry, 'summary', '')
            or getattr(entry, 'description', '')
            or ''
        )
        summary = _strip_html(raw_summary)[:_SUMMARY_MAX]
        content = _extract_content(entry)
        link = getattr(entry, 'link', '') or ''

        items.append({
            "source":    source["name"],
            "lang":      source.get("lang", "en"),
            "title":     title,
            "summary":   summary,
            "content":   content,
            "link":      link,
            "published": published.isoformat() if published else None,
        })

    log.info(f"[{source['name']}] {len(items)} items within {window_hours}h")
    return items


def fetch_all(news_sources: list[dict], window_hours: int = 24) -> list[dict]:
    articles: list[dict] = []
    for src in news_sources:
        articles.extend(fetch_source(src, window_hours=window_hours))

    for i, a in enumerate(articles):
        a['id'] = i

    log.info(f"Total fetched: {len(articles)}")
    return articles
