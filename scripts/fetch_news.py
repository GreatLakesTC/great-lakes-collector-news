
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from html import unescape

# The Great Lakes Collector - Automated News Feed

FEEDS = {
    "MLB": "https://www.mlb.com/feeds/news/rss.xml",
    "CBS MLB": "https://www.cbssports.com/rss/headlines/mlb",
    "CBS NFL": "https://www.cbssports.com/rss/headlines/nfl",
    "CBS NBA": "https://www.cbssports.com/rss/headlines/nba",
}

KEYWORDS = [
    "rookie", "prospect", "call-up", "debut",
    "trade", "traded", "injury", "injured",
    "breakout", "record", "mvp", "award",
    "topps", "bowman", "panini", "refractor",
    "trading card", "sports card", "checklist",
    "release", "grading", "psa", "beckett",
    "auction", "collectible"
]

MAX_ARTICLES = 30
OUTPUT = Path("docs/news.json")


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def fetch_feed(source, url):
    articles = []

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GreatLakesCollectorNews/1.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

        for item in root.findall(".//item"):
            title = clean_text(item.findtext("title"))
            link = (item.findtext("link") or "").strip()
            description = clean_text(item.findtext("description"))
            published = item.findtext("pubDate") or ""

            if not title or not link.startswith("https://"):
                continue

            
search_text = title.lower()

# Exclude promotions, betting content, and unrelated offers
EXCLUDED_TERMS = [
    "promo code",
    "bonus bets",
    "sportsbook",
    "betting odds",
    "kalshi",
    "prediction market",
    "parlay",
    "free bets",
    "how to bet",
    "best bets",
]

if any(term in search_text for term in EXCLUDED_TERMS):
    continue


            if not any(word in search_text for word in KEYWORDS):
                continue

            try:
                date = parsedate_to_datetime(published)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                timestamp = date.timestamp()
            except (ValueError, TypeError, OverflowError):
                timestamp = 0

            articles.append({
                "title": title,
                "url": link,
                "source": source,
                "published": published,
                "timestamp": timestamp
            })

        print(f"{source}: found {len(articles)} matching articles")

    except Exception as error:
        print(f"Could not fetch {source}: {error}")

    return articles


def main():
    articles = []

    for source, url in FEEDS.items():
        articles.extend(fetch_feed(source, url))

    unique = {}

    for article in articles:
        unique[article["url"]] = article

    results = sorted(
        unique.values(),
        key=lambda article: article["timestamp"],
        reverse=True
    )[:MAX_ARTICLES]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Preserve the last successful feed if all sources fail.
    if not results and OUTPUT.exists():
        print("No articles found; keeping existing news.json")
        return

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "articles": results
    }

    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Saved {len(results)} articles to {OUTPUT}")


if __name__ == "__main__":
    main()
