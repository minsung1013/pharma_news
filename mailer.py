import smtplib
import time
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

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
  margin: 14px 0 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.item { margin: 3px 0 3px 14px; line-height: 1.5; }
.highlight-card {
  background: #f0f7ff;
  border-left: 4px solid #2e86c1;
  padding: 14px 16px;
  margin: 18px 0;
  border-radius: 0 6px 6px 0;
}
.hl-category {
  font-size: 11px;
  font-weight: bold;
  color: #2e86c1;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}
.hl-title { font-size: 15px; font-weight: bold; margin-bottom: 10px; }
.hl-section {
  font-size: 11px;
  font-weight: bold;
  color: #888;
  margin: 10px 0 4px;
  text-transform: uppercase;
}
.hl-body { line-height: 1.7; white-space: pre-wrap; }
.implication {
  background: #fffde7;
  border-left: 3px solid #f9a825;
  padding: 8px 12px;
  margin-top: 8px;
  border-radius: 0 4px 4px 0;
  line-height: 1.7;
  white-space: pre-wrap;
}
.hl-footer { font-size: 12px; color: #888; margin-top: 10px; }
.digest-block { background: #fff; border: 1px solid #e0e0e0; padding: 14px 16px; border-radius: 6px; }
.digest-label { font-weight: bold; color: #333; margin: 12px 0 4px; }
a { color: #2e86c1; text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 28px 0; }
.en-sub { color: #888; font-size: 12px; }
.hl-title-en { font-size: 12px; color: #888; margin-top: 2px; margin-bottom: 8px; }
"""


def _e(text: str) -> str:
    """Minimal HTML escape."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def _news_section(articles: list[dict], item_type: str) -> str:
    sources: dict[str, list[dict]] = {}
    for a in articles:
        if a.get("type") == item_type:
            sources.setdefault(a["source"], []).append(a)

    if not sources:
        return "<p><em>해당 항목 없음</em></p>"

    html = ""
    for source, items in sources.items():
        html += f'<div class="source-label">{_e(source)}</div>'
        for a in items:
            korean  = _e(a.get("korean_summary") or a.get("title", ""))
            link    = a.get("link", "#")
            is_en   = a.get("lang") == "en"
            orig_en = _e(a.get("title", ""))

            if is_en and korean and korean != orig_en:
                html += (
                    f'<div class="item">• {korean}'
                    f' <span class="en-sub">/ {orig_en}</span>'
                    f' <a href="{link}">[link]</a></div>'
                )
            else:
                html += f'<div class="item">• {korean} <a href="{link}">[링크]</a></div>'
    return html


def _digest_section(digest: Optional[dict]) -> str:
    if not digest:
        return "<p><em>종합 분석 생성 실패</em></p>"

    html = '<div class="digest-block">'
    if trend := digest.get("trend"):
        html += f'<div class="digest-label">핵심 트렌드</div><p>{_e(trend)}</p>'
    if movements := digest.get("movements"):
        html += '<div class="digest-label">빅파마·바이오텍 주요 움직임</div><ul>'
        html += "".join(f"<li>{_e(m)}</li>" for m in movements)
        html += "</ul>"
    html += "</div>"
    return html


def _highlights_section(highlights: list[dict], all_articles: list[dict]) -> str:
    if not highlights:
        return "<p><em>관심 키워드 하이라이트 없음</em></p>"

    dedup_counts: dict[int, int] = {}
    for a in all_articles:
        gid = a.get("dedup_group_id", a["id"])
        dedup_counts[gid] = dedup_counts.get(gid, 0) + 1

    html = ""
    for h in highlights:
        detail = h.get("_detail") or {}
        gid = h.get("dedup_group_id", h["id"])
        related = dedup_counts.get(gid, 1) - 1

        title_kr      = _e(detail.get("title_kr") or h.get("title", ""))
        title_en      = _e(h.get("title", ""))
        summary_text  = _e(detail.get("summary")  or h.get("korean_summary", ""))
        impl_text     = _e(detail.get("implication", ""))
        category      = _e(h.get("category", ""))
        keywords      = _e(", ".join(h.get("matched_keywords", [])))
        link          = h.get("link", "#")
        is_en         = h.get("lang") == "en"

        html += f'<div class="highlight-card">'
        html += f'<div class="hl-category">🏷 {category}</div>'
        html += f'<div class="hl-title">{title_kr}</div>'
        if is_en and title_kr != title_en:
            html += f'<div class="hl-title-en">{title_en}</div>'
        html += f'<div class="hl-section">요약</div>'
        html += f'<div class="hl-body">{summary_text}</div>'

        if impl_text:
            html += f'<div class="hl-section">BD 시사점</div>'
            html += f'<div class="implication">{impl_text}</div>'

        html += f'<div class="hl-footer"><a href="{link}">[원문]</a>'
        if related > 0:
            html += f"&nbsp;&nbsp;관련 보도 {related}건"
        if keywords:
            html += f"&nbsp;&nbsp;키워드: {keywords}"
        html += "</div></div>"

    return html


def build_html(
    articles: list[dict],
    highlights: list[dict],
    digest: Optional[dict],
    date_str: str,
) -> str:
    news_html    = _news_section(articles, "news")
    papers_html  = _news_section(articles, "paper")
    digest_html  = _digest_section(digest)
    hl_html      = _highlights_section(highlights, articles)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>BioPharma Digest {date_str}</title>
  <style>{_CSS}</style>
</head>
<body>
<h1>BioPharma Digest &mdash; {date_str}</h1>

<h2>🔍 오늘의 종합</h2>
{digest_html}

<hr>

<h2>⭐ 핵심 하이라이트 Top 5</h2>
{hl_html}

<hr>

<h2>📰 오늘의 뉴스</h2>
{news_html}

<h2>📑 신규 연구 논문</h2>
{papers_html}

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
    subject = f"[BioPharma Digest] {date_str} 오늘의 뉴스·논문"
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
