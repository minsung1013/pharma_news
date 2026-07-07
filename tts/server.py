"""팟캐스트 피드 + 오디오 서빙 (Flask).

- GET /feed.xml           : RSS 피드
- GET /audio/<file>.mp3   : 오디오 (Range 요청 지원 → 스크러빙 가능)
- GET /                   : 간단한 웹 플레이어 (팟캐스트 앱 없이 브라우저 청취용)

Tailscale/Cloudflare Tunnel 뒤에 두고 모바일에서 접속한다.
"""
import logging

from flask import Flask, Response, send_from_directory
from xml.sax.saxutils import escape

from . import config, feed

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)


@app.route("/feed.xml")
def feed_xml():
    xml = feed.build_feed(feed.load_episodes())
    return Response(xml, mimetype="application/rss+xml")


@app.route("/audio/<path:filename>")
def audio(filename):
    # send_from_directory → send_file 은 Range/조건부 요청을 기본 지원
    return send_from_directory(
        config.AUDIO_DIR.resolve(), filename,
        mimetype="audio/mpeg", conditional=True,
    )


@app.route("/")
def index():
    eps = sorted(feed.load_episodes(), key=lambda x: x.get("pubDate", ""), reverse=True)
    rows = []
    for e in eps:
        rows.append(f"""<li>
  <div class="t">{escape(e['title'])}</div>
  <audio controls preload="none" src="/audio/{escape(e['file'])}"></audio>
  <a href="{escape(e.get('url',''))}" target="_blank">원문</a>
</li>""")
    html = f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(config.PODCAST_TITLE)}</title>
<style>
 body{{font-family:-apple-system,system-ui,sans-serif;margin:0;padding:16px;background:#111;color:#eee}}
 h1{{font-size:18px}} ul{{list-style:none;padding:0}}
 li{{padding:12px 0;border-bottom:1px solid #333}}
 .t{{font-size:15px;margin-bottom:6px}} audio{{width:100%}}
 a{{color:#6ab7ff;font-size:13px}}
 .feed{{font-size:13px;color:#999}}
</style></head><body>
<h1>{escape(config.PODCAST_TITLE)}</h1>
<p class="feed">팟캐스트 앱 구독 URL: <code>{escape(config.PODCAST_BASE_URL)}/feed.xml</code></p>
<ul>{''.join(rows)}</ul>
</body></html>"""
    return Response(html, mimetype="text/html")


def main():
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, threaded=True)


if __name__ == "__main__":
    main()
