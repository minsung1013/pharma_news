import smtplib
import time
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config as cfg
import curator

log = logging.getLogger(__name__)

_CSS = """
body {
  font-family: -apple-system, Arial, sans-serif;
  font-size: 14px;
  color: #222;
  max-width: 820px;
  margin: 0 auto;
  padding: 24px 20px;
  background: #fafafa;
}
h1 { font-size: 20px; color: #1a3a5c; margin-bottom: 4px; }
h2 {
  font-size: 16px;
  color: #1a5276;
  border-bottom: 2px solid #1a5276;
  padding-bottom: 4px;
  margin: 32px 0 12px;
}
.source-label {
  font-weight: bold;
  color: #555;
  font-size: 12px;
  margin: 16px 0 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.item { margin: 4px 0 4px 4px; line-height: 1.5; }
.highlight-card {
  background: #f0f7ff;
  border-left: 4px solid #2e86c1;
  padding: 14px 16px;
  margin: 16px 0;
  border-radius: 0 6px 6px 0;
}
.hl-top { margin-bottom: 6px; }
.hl-title { font-size: 15px; font-weight: bold; margin: 6px 0 8px; }
.hl-body { line-height: 1.7; white-space: pre-wrap; color: #333; }
.hl-footer { font-size: 12px; color: #888; margin-top: 10px; }
.badge {
  display: inline-block; font-size: 10px; font-weight: bold;
  padding: 1px 7px; border-radius: 10px; margin-right: 4px;
  vertical-align: middle; letter-spacing: 0.02em;
}
.badge-cat   { background: #2e86c1; color: #fff; text-transform: uppercase; }
.badge-score { background: #7d3cff; color: #fff; }
.stats-block { background: #fff; border: 1px solid #e0e0e0; padding: 14px 16px; border-radius: 6px; }
.stats-row { margin: 4px 0; }
.stats-label { font-weight: bold; color: #333; }
.kw { color: #999; font-size: 12px; }
a { color: #2e86c1; text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 28px 0; }
.en-sub { color: #888; font-size: 12px; }
"""


def _e(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _badges(a: dict) -> str:
    return (
        f'<span class="badge badge-cat">🏷 {_e(a.get("category", "Other"))}</span>'
        f'<span class="badge badge-score">▲ {a.get("score", 0)}</span>'
    )


# ── [2] 통계 ─────────────────────────────────────────────────────────────────
def _stats_section(articles: list[dict]) -> str:
    total = len(articles)
    cats = curator.category_counts(articles)
    orgs = curator.top_organizations(articles, cfg.TOP_ORGS)

    cat_str = " · ".join(f"{_e(c)} {n}" for c, n in cats) or "—"
    org_str = " · ".join(f"{_e(name)} ({n})" for name, _t, n in orgs) or "—"

    return (
        '<div class="stats-block">'
        f'<div class="stats-row"><span class="stats-label">총 통과 기사</span> {total}건</div>'
        f'<div class="stats-row"><span class="stats-label">카테고리별</span> {cat_str}</div>'
        f'<div class="stats-row"><span class="stats-label">주요 등장 기관</span> {org_str}</div>'
        '</div>'
    )


# ── [3] 하이라이트 ────────────────────────────────────────────────────────────
def _highlights_section(articles: list[dict]) -> str:
    highlights = [a for a in articles if a.get("is_highlight")]
    if not highlights:
        return "<p><em>하이라이트 없음</em></p>"

    html = ""
    for a in highlights:
        body = a.get("content") or a.get("summary") or ""
        if len(body) > cfg.MAX_HL_CHARS:
            log.info(f"  하이라이트 제외(본문 {len(body)}자 > {cfg.MAX_HL_CHARS}): {a.get('title','')[:50]}")
            continue

        title = _e(a.get("title", ""))
        link = a.get("link", "#")
        kws = _e(", ".join(a.get("matched_keywords", [])[:8]))

        html += '<div class="highlight-card">'
        html += f'<div class="hl-top">{_badges(a)}</div>'
        html += f'<div class="hl-title">{title}</div>'
        html += f'<div class="hl-body">{_e(body)}</div>'
        html += f'<div class="hl-footer"><a href="{link}">[원문]</a>'
        if kws:
            html += f'&nbsp;&nbsp;키워드: {kws}'
        html += '</div></div>'
    return html or "<p><em>하이라이트 없음(본문 길이 초과 제외)</em></p>"


# ── [4] 소스별 뉴스 ───────────────────────────────────────────────────────────
def _news_section(articles: list[dict]) -> str:
    # 하이라이트·중복 제외한 대표 기사만, 소스별 그룹
    news = [a for a in articles if not a.get("is_highlight") and not a.get("is_dup")]
    if not news:
        return "<p><em>추가 뉴스 없음</em></p>"

    sources: dict[str, list[dict]] = {}
    for a in news:
        sources.setdefault(a.get("source", "기타"), []).append(a)

    html = ""
    for source, items in sources.items():
        items.sort(key=lambda a: a.get("score", 0), reverse=True)
        html += f'<div class="source-label">{_e(source)}</div>'
        for a in items:
            summary = a.get("summary") or ""
            if len(summary) > cfg.MAX_NEWS_CHARS:
                log.info(f"  뉴스 제외(요약 {len(summary)}자 > {cfg.MAX_NEWS_CHARS}): {a.get('title','')[:50]}")
                continue
            title = _e(a.get("title", ""))
            link = a.get("link", "#")
            score = a.get("score", 0)
            html += (
                f'<div class="item">'
                f'<span class="badge badge-score">▲ {score}</span> '
                f'<strong>{title}</strong> <a href="{link}">[link]</a>'
            )
            if summary:
                html += f'<br><span class="en-sub">{_e(summary)}</span>'
            html += '</div>'
    return html


def build_html(articles: list[dict], date_str: str) -> str:
    stats_html = _stats_section(articles)
    hl_html    = _highlights_section(articles)
    news_html  = _news_section(articles)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>BioPharma·AI Digest {date_str}</title>
  <style>{_CSS}</style>
</head>
<body>
<h1>BioPharma &amp; AI Digest &mdash; {date_str}</h1>

<h2>🔍 오늘의 통계</h2>
{stats_html}

<hr>

<h2>⭐ 핵심 하이라이트</h2>
{hl_html}

<hr>

<h2>📰 오늘의 뉴스</h2>
{news_html}

</body>
</html>"""


def send_mail(
    html: str,
    date_str: str,
    gmail_address: str,
    app_password: str,
    recipients: list[str],
    max_retries: int = 3,
) -> None:
    subject = f"[BioPharma·AI Digest] {date_str} 오늘의 뉴스"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    for attempt in range(max_retries):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                s.login(gmail_address, app_password)
                s.sendmail(gmail_address, recipients, msg.as_string())
            log.info(f"Mail sent → {recipients}")
            return
        except Exception as e:
            wait = 2 ** attempt
            log.warning(f"SMTP attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                raise
