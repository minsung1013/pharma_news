"""episodes.json → 팟캐스트 RSS(feed.xml) 생성.

에피소드 메타는 data/audio/episodes.json 에 누적된다. 각 항목:
  {guid, title, url(원문), file, bytes, duration_sec, pubDate(RFC822)}
"""
import json
from email.utils import format_datetime
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from . import config


def load_episodes() -> list[dict]:
    if config.EPISODES_JSON.exists():
        return json.loads(config.EPISODES_JSON.read_text(encoding="utf-8"))
    return []


def save_episodes(eps: list[dict]) -> None:
    config.EPISODES_JSON.parent.mkdir(parents=True, exist_ok=True)
    config.EPISODES_JSON.write_text(
        json.dumps(eps, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _fmt_duration(sec: float | None) -> str:
    if not sec:
        return "0:00"
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def build_feed(eps: list[dict]) -> str:
    base = config.PODCAST_BASE_URL
    cover = config.COVER_URL
    now = format_datetime(datetime.now(timezone.utc))
    items: list[str] = []
    # 최신순
    for e in sorted(eps, key=lambda x: x.get("pubDate", ""), reverse=True):
        file_url = f"{config.AUDIO_BASE_URL}/{e['file']}"
        desc = e.get("summary") or e.get("url", "")
        items.append(f"""    <item>
      <title>{escape(e['title'])}</title>
      <guid isPermaLink="false">{escape(e['guid'])}</guid>
      <link>{escape(e.get('url', base))}</link>
      <pubDate>{e['pubDate']}</pubDate>
      <enclosure url="{escape(file_url)}" length="{e.get('bytes', 0)}" type="audio/mpeg"/>
      <itunes:duration>{_fmt_duration(e.get('duration_sec'))}</itunes:duration>
      <itunes:image href="{escape(cover)}"/>
      <itunes:explicit>false</itunes:explicit>
      <description>{escape(desc)}</description>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{escape(config.PODCAST_TITLE)}</title>
    <link>{escape(base)}</link>
    <language>{escape(config.PODCAST_LANG)}</language>
    <description>{escape(config.PODCAST_DESC)}</description>
    <itunes:author>{escape(config.PODCAST_AUTHOR)}</itunes:author>
    <itunes:summary>{escape(config.PODCAST_DESC)}</itunes:summary>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <itunes:category text="Science"/>
    <itunes:category text="News"/>
    <itunes:owner>
      <itunes:name>{escape(config.PODCAST_AUTHOR)}</itunes:name>
      <itunes:email>{escape(config.PODCAST_OWNER_EMAIL)}</itunes:email>
    </itunes:owner>
    <itunes:image href="{escape(cover)}"/>
    <image>
      <url>{escape(cover)}</url>
      <title>{escape(config.PODCAST_TITLE)}</title>
      <link>{escape(base)}</link>
    </image>
    <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""


def write_feed(eps: list[dict], path: Path | None = None) -> Path:
    path = path or config.FEED_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_feed(eps), encoding="utf-8")
    return path
