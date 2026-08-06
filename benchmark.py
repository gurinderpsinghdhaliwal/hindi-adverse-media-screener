"""
Benchmark: native-language Hindi screening vs translate-then-screen.

For each article, run TWO pipelines:
  1. NATIVE:    send Hindi text to the screener as-is.
  2. TRANSLATE: ask Gemini to translate Hindi -> English first,
                then send the English translation to the screener.

Compare adverse-entity counts and specific catches to quantify
the value of screening in the source language.
"""
import json
import os
import time
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

from fetch_news import fetch_recent
from screener import screen_article, SYSTEM_PROMPT, MODEL

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 6.5s pause keeps us safely under 10 req/min on gemini-2.5-flash free tier
PAUSE = 5.0  # keeps us under 15 req/min on gemini-2.5-flash-lite free tier (~12/min effective)


def translate_to_english(hindi_text: str) -> str:
    """Translate Hindi -> English. Simulates a 'translate-first' pipeline."""
    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(temperature=0.1),
        contents=(
            "Translate the following Hindi text into English. "
            "Return only the English translation, no preamble.\n\n"
            + hindi_text
        ),
    )
    return response.text


def screen_english(english_text: str, source_url: str = "") -> dict:
    """Screen English text using the same prompt (adjusted for language)."""
    # Remove the "do not translate" instruction since input is already English.
    en_prompt = SYSTEM_PROMPT.replace(
        "Read the article in the original Hindi. Do NOT translate it. Analyse it in-language.",
        "Read the article carefully and analyse it.",
    )
    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=en_prompt,
            response_mime_type="application/json",
            temperature=0.1,
        ),
        contents=f"Article source: {source_url}\n\nArticle text:\n{english_text}",
    )
    return json.loads(response.text)


def adverse_entities(screening: dict) -> set[str]:
    """Return the set of entity names flagged as adverse (case-insensitive)."""
    return {
        e["name"].strip().lower()
        for e in screening.get("entities", [])
        if e.get("risk_category") not in (None, "NONE")
    }


def main(sample_size: int = 15, max_per_query: int = 3):
    """
    Run the benchmark.

    sample_size: number of articles to benchmark.
    Each article costs 3 API calls (native, translate, translate-screen),
    so 15 articles = 45 calls, well under 250/day free tier.
    """
    articles = fetch_recent(max_per_query=max_per_query)[:sample_size]
    print(f"\nBenchmarking {len(articles)} articles "
          f"({len(articles) * 3} total API calls)...\n")

    comparisons = []
    native_total = 0
    translate_total = 0
    native_only_catches = 0
    translate_only_catches = 0
    both_agreed = 0

    for i, art in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {art.title[:70]}")

        def with_retry(fn, *args, **kwargs):
            """Retry once on rate-limit (429), give up on anything else."""
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print(f"    ~ rate-limited, waiting 30s and retrying...")
                    time.sleep(30)
                    return fn(*args, **kwargs)
                raise

        try:
            native = with_retry(screen_article, art.text, source_url=art.url)
            time.sleep(PAUSE)
            english = with_retry(translate_to_english, art.text)
            time.sleep(PAUSE)
            translated = with_retry(screen_english, english, source_url=art.url)
            time.sleep(PAUSE)
        except Exception as e:
            print(f"    ! pipeline failed: {e}")
            continue

        n_names = adverse_entities(native)
        t_names = adverse_entities(translated)

        native_total += len(n_names)
        translate_total += len(t_names)

        native_only = n_names - t_names
        translate_only = t_names - n_names
        agreed = n_names & t_names

        native_only_catches += len(native_only)
        translate_only_catches += len(translate_only)
        both_agreed += len(agreed)

        print(f"    native: {len(n_names)} adverse | translate: {len(t_names)} adverse | agreed: {len(agreed)}")
        if native_only:
            print(f"    native caught (translate missed): {sorted(native_only)}")
        if translate_only:
            print(f"    translate caught (native missed): {sorted(translate_only)}")

        comparisons.append({
            "url": art.url,
            "title": art.title,
            "source": art.source,
            "native_adverse_count": len(n_names),
            "translate_adverse_count": len(t_names),
            "native_only_entities": sorted(native_only),
            "translate_only_entities": sorted(translate_only),
            "agreed_entities": sorted(agreed),
            "native_result": native,
            "translated_english_text": english,
            "translate_result": translated,
        })

    # ---- Summary ----
    n_articles = len(comparisons)
    print(f"\n{'=' * 62}")
    print(f"BENCHMARK SUMMARY ({n_articles} articles, model={MODEL})")
    print(f"{'=' * 62}")
    print(f"Adverse entities flagged — native pipeline:    {native_total}")
    print(f"Adverse entities flagged — translate pipeline: {translate_total}")
    print(f"Agreed by both pipelines:                      {both_agreed}")
    print(f"Caught only by native (missed by translate):   {native_only_catches}")
    print(f"Caught only by translate (missed by native):   {translate_only_catches}")
    if translate_total > 0:
        uplift = (native_total - translate_total) / translate_total * 100
        print(f"\nNative pipeline uplift over translate-first: {uplift:+.1f}%")
    print(f"{'=' * 62}")

    os.makedirs("results", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"results/benchmark_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "model": MODEL,
                "articles": n_articles,
                "native_total_adverse": native_total,
                "translate_total_adverse": translate_total,
                "both_agreed": both_agreed,
                "native_only_catches": native_only_catches,
                "translate_only_catches": translate_only_catches,
            },
            "comparisons": comparisons,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved full benchmark to {out_path}")


if __name__ == "__main__":
    main(sample_size=15)