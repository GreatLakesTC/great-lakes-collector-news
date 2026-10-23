
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
    # Rookies and prospects
    "rookie",
    "prospect",
    "debut",
    "call-up",
    "called up",
    "breakout",
    "rising star",
    "first career",

    # Major player developments
    "rookie of the year",
    "alcs mvp",
    "nlcs mvp",
    "world series mvp",
    "finals mvp",
    "named mvp",
    "wins mvp",
    "record-breaking",
    "historic performance",
    "milestone",
    "blockbuster trade",
    "traded to",
    "season-ending injury",
    "retirement",

    # Trading card news
    "trading card",
    "sports card",
    "topps",
    "bowman",
    "panini",
    "refractor",
    "rookie card",
    "card checklist",
    "hobby box",
    "card grading",
    "psa grading",
    "beckett grading",
    "card auction"
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

    
    excluded_terms = [
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
        "mvp odds",
        "odds and predictions",
        "expert picks",
        "lost all respect",
        "facing former teams",
        "coaches fined",
        "head coaches with fines",
    ]


    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

        for item in root.findall(".//item"):
            title = clean_text(item.findtext("title"))
            link = (item.findtext("link") or "").strip()
            published = item.findtext("pubDate") or ""

            if not title or not link.startswith("https://"):
                continue

            search_text = title.lower()

            # Exclude betting and promotional headlines
            if any(term in search_text for term in excluded_terms):
                continue

            # Only include relevant collector-focused topics
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
                "published": published.strip(),
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
