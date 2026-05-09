import csv
import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

COLUMNS = ["date", "organization", "org_type", "role", "category", "content", "link", "source"]


def append_organizations(articles: list[dict], csv_path: str) -> int:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    write_header = not path.exists() or path.stat().st_size == 0
    today = date.today().isoformat()

    seen_dedup: set[int] = set()
    rows: list[dict] = []

    for article in articles:
        orgs = article.get("organizations", [])
        if not orgs:
            continue

        dedup_id = article.get("dedup_group_id", article["id"])
        if dedup_id in seen_dedup:
            continue
        seen_dedup.add(dedup_id)

        for org in orgs:
            if not org.get("name"):
                continue
            rows.append({
                "date":         today,
                "organization": org["name"],
                "org_type":     org.get("org_type", "other"),
                "role":         org.get("role", "other"),
                "category":     article.get("category", ""),
                "content":      article.get("korean_summary", ""),
                "link":         article.get("link", ""),
                "source":       article.get("source", ""),
            })

    try:
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)
        log.info(f"CSV: appended {len(rows)} org rows → {path}")
    except Exception as e:
        log.warning(f"CSV append failed (non-fatal): {e}")

    return len(rows)
