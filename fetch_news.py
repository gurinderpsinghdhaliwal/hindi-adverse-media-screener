"""
Fetch recent Hindi financial-news articles from Google News RSS.

Google News aggregates thousands of Hindi outlets and returns short article
summaries in the feed itself — clean, paywall-free, screening-ready text.
"""
import urllib.parse
import feedparser
from dataclasses import dataclass


@dataclass
class Article:
    title: str
    url: str
    published: str
    text: str
    source: str


# Hindi search queries chosen for adverse-media relevance.
# Each query targets a category of financial crime coverage in Hindi press.
QUERIES = [
    ("Enforcement Directorate arrests", "प्रवर्तन निदेशालय गिरफ्तार"),
    ("Money laundering / hawala", "धन शोधन हवाला"),
    ("Financial fraud", "वित्तीय धोखाधड़ी"),
    ("SEBI action", "सेबी कार्रवाई"),
    ("Corruption charges", "भ्रष्टाचार आरोप"),
    ("CBI raid", "सीबीआई छापा"),
    ("General business news", "व्यापार समाचार"),  # includes non-adverse for balance
]

# Google News RSS: hl=hi (Hindi UI), gl=IN (India), ceid=IN:hi (edition)
GNEWS_TEMPLATE = "https://news.google.com/rss/search?q={q}&hl=hi&gl=IN&ceid=IN:hi"


def fetch_query(label: str, hindi_query: str, max_results: int = 5) -> list[Article]:
    """Pull top articles for one Hindi search query from Google News."""
    url = GNEWS_TEMPLATE.format(q=urllib.parse.quote(hindi_query))
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries[:max_results]:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        # Google News summary contains HTML — strip tags crudely
        from bs4 import BeautifulSoup
        clean_summary = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
        # The article body for screening = title + summary
        # (Both are already in Hindi; summary is 2-4 sentence context)
        body = f"{title}\n\n{clean_summary}"
        if len(body) < 60:
            continue
        articles.append(Article(
            title=title,
            url=entry.get("link", ""),
            published=entry.get("published", ""),
            text=body,
            source=f"Google News: {label}",
        ))
    return articles


def fetch_recent(max_per_query: int = 5) -> list[Article]:
    """Pull articles across all queries."""
    articles = []
    for label, hindi_query in QUERIES:
        print(f"Fetching '{label}' ({hindi_query})...")
        found = fetch_query(label, hindi_query, max_results=max_per_query)
        print(f"    -> {len(found)} articles")
        articles.extend(found)
    return articles


if __name__ == "__main__":
    arts = fetch_recent(max_per_query=3)
    print(f"\nFetched {len(arts)} articles total\n")
    for a in arts[:3]:
        print(f"--- {a.source} ---")
        print(f"Title: {a.title}")
        print(f"URL: {a.url}")
        print(f"Body preview: {a.text[:250]}...")
        print()