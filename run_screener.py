"""
End-to-end: fetch recent Hindi news, screen for adverse media, save results.
"""
import json
import os
import time
from datetime import datetime
from fetch_news import fetch_recent
from screener import screen_article


def main(max_per_query: int = 3, pause_seconds: float = 6.5):
    """
    Fetch, screen, save.

    pause_seconds: Gemini free tier caps at 10 requests/minute.
    6.5s between calls keeps us safely under (~9/min).
    """
    os.makedirs("results", exist_ok=True)
    articles = fetch_recent(max_per_query=max_per_query)
    print(f"\nScreening {len(articles)} articles...\n")

    results = []
    for i, art in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {art.title[:70]}")
        try:
            screening = screen_article(art.text, source_url=art.url)
        except Exception as e:
            print(f"    ! screening failed: {e}")
            time.sleep(pause_seconds)
            continue

        results.append({
            "source": art.source,
            "url": art.url,
            "title": art.title,
            "published": art.published,
            "screening": screening,
        })

        # Print adverse hits inline so you can see the pipeline working
        adverse = [
            e for e in screening.get("entities", [])
            if e.get("risk_category") not in (None, "NONE")
        ]
        if adverse:
            print(f"    -> {len(adverse)} adverse entity/entities flagged:")
            for e in adverse:
                print(f"       - {e['name']}: {e['risk_category']} ({e['risk_severity']})")
        else:
            print(f"    -> no adverse entities")

        # Rate-limit pacing
        if i < len(articles):
            time.sleep(pause_seconds)

    # Save everything
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"results/screening_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} screening results to {out_path}")


if __name__ == "__main__":
    main(max_per_query=3)