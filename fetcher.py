import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser

log = logging.getLogger(__name__)

_HTML_TAG   = re.compile(r'<[^>]+>')
_WHITESPACE = re.compile(r'\s+')


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


def fetch_source(source: dict) -> list[dict]:
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

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
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
        summary = _strip_html(raw_summary)[:1500]
        link = getattr(entry, 'link', '') or ''

        items.append({
            "source":    source["name"],
            "type":      source["type"],
            "lang":      source.get("lang", "en"),
            "title":     title,
            "summary":   summary,
            "link":      link,
            "published": published.isoformat() if published else None,
        })

    log.info(f"[{source['name']}] {len(items)} items within 24h")
    return items


def fetch_all(
    news_sources: list[dict],
    paper_sources: list[dict],
) -> list[dict]:
    articles: list[dict] = []

    for src in news_sources:
        articles.extend(fetch_source(src))
    for src in paper_sources:
        articles.extend(fetch_source(src))

    for i, a in enumerate(articles):
        a['id'] = i

    log.info(f"Total fetched: {len(articles)} (news + papers)")
    return articles
