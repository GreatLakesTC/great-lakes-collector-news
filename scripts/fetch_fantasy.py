
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

FEEDS = {
    "Fantasy NFL": [
        ("FantasyPros", "https://www.fantasypros.com/content/nfl/feed/"),
        ("RotoWire", "https://www.rotowire.com/rss/news.php?sport=NFL"),
    ],
    "Fantasy NBA": [
        ("RotoWire", "https://www.rotowire.com/rss/news.php?sport=NBA"),
    ],
    "Fantasy MLB": [
        ("RotoWire", "https://www.rotowire.com/rss/news.php?sport=MLB"),
    ],
}

KEYWORDS = [
    "fantasy", "start", "sit", "waiver", "pickup",
    "sleeper", "breakout", "injury", "injured",
    "questionable", "doubtful", "ruled out",
    "out for", "return", "practice", "limited",
    "inactive", "available", "lineup",
    "starting", "starter", "bench", "rotation",
    "minutes", "workload", "role", "targets",
    "touches", "snaps", "receptions",
    "rushing", "passing", "touchdown",
    "rebound", "assist", "points",
    "home run", "strikeout", "promotion",
    "called up", "closer", "save", "ranking",
    "projection", "trade", "depth chart",
    "rest", "day-to-day", "hamstring",
    "ankle", "knee", "shoulder"
]

EXCLUSIONS = [
    "promo code", "bonus bets", "sportsbook",
    "betting odds", "best bets", "parlay",
    "kalshi", "prediction market",
    "gambling", "casino"
]

MAX_AGE_DAYS = 10
MAX_PER_SPORT = 20



def clean_text(value):
    import html

    text = value or ""

    # Decode HTML entities, including nested encodings
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text



def read_feed(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "GreatLakesCollectorNews/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml"
        }
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return ET.fromstring(response.read())


def get_date(item):
    raw = item.findtext("pubDate") or ""
    if not raw:
        return None

    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def collect():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    articles = []
    seen = set()
    counts = {}

    for sport, sources in FEEDS.items():
        found = []

        for source_name, url in sources:
            try:
                root = read_feed(url)
                items = root.findall(".//item")

                source_count = 0

                for item in items:
                    title = clean_text(item.findtext("title"))
                    link = (item.findtext("link") or "").strip()
                    description = clean_text(
                        item.findtext("description")
                    )

                    if not title or not link:
                        continue

                    published = get_date(item)
                    if published is None or published < cutoff:
                        continue

                    search_text = (
                        title + " " + description
                    ).lower()

                    if any(word in search_text for word in EXCLUSIONS):
                        continue

                    if not any(word in search_text for word in KEYWORDS):
                        continue

                    key = link.split("?")[0].rstrip("/")
                    if key in seen:
                        continue

                    seen.add(key)

                    found.append({
                        "title": title,
                        "url": link,
                        "source": source_name,
                        "sport": sport,
                        "published": published.isoformat(),
                        "timestamp": int(published.timestamp()),
                        
"summary": (
    description[:197].rsplit(" ", 1)[0] + "..."
    if len(description) > 200
    else description
)

                    })
                    source_count += 1

                print(f"{sport} / {source_name}: {source_count} articles")

            except Exception as exc:
                print(f"Could not fetch {sport} / {source_name}: {exc}")

        found.sort(
            key=lambda article: article["timestamp"],
            reverse=True
        )

        selected = found[:MAX_PER_SPORT]
        counts[sport] = len(selected)
        articles.extend(selected)

    articles.sort(
        key=lambda article: article["timestamp"],
        reverse=True
    )

    return {
        "updated_at": now.isoformat(),
        "count": len(articles),
        "counts": counts,
        "articles": articles
    }


def main():
    data = collect()

    output = Path("docs/fantasy-news.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Saved {data['count']} fantasy articles to {output}")


if __name__ == "__main__":
    main()
