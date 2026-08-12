# Hindi-Native Adverse Media Screener

A working prototype that reads Hindi-language financial news and flags people or entities linked to fraud, money laundering, corruption, and other financial crimes. This is the kind of screening a bank's compliance team does when onboarding a new customer or reviewing an existing one.

The point of the project isn't the screening itself. It's the comparison. I ran two versions of the same pipeline on the same articles. One reads the Hindi directly. The other translates it to English first and then screens the English. Looking at where the two versions disagree is where the interesting result is.

## Why I built this

I'm applying for finance-adjacent AI roles in Hong Kong, and adverse media screening is one of the areas where AI is quietly reshaping how compliance actually gets done. Most existing tools were built for English-language sources. When they process non-Latin scripts like Hindi, Chinese, or Arabic, they usually translate first and then screen. That step introduces silent errors: a person's name gets romanised one way in one article and a different way in another, and downstream systems treat them as two different people.

I wanted to see how big that problem actually is on a real dataset, not just read about it in a whitepaper.

## What it does

The pipeline has three pieces.

The **news fetcher** pulls recent Hindi articles from Google News searches on financial-crime terms (`प्रवर्तन निदेशालय गिरफ्तार`, meaning "Enforcement Directorate arrests", and similar).

The **screener** sends each article to Google's Gemini API and asks it to identify people or organisations mentioned, classify each one against a set of financial-crime risk categories (fraud, money laundering, sanctions, corruption, regulatory action, and so on), and return the result as structured JSON with a supporting quote from the article.

The **benchmark** runs each article through the screener twice. Once in the original Hindi, once after translating to English. Then it compares what each version caught.

## What I found

I ran the benchmark on 15 Hindi financial-news articles pulled fresh from Google News. The pipelines flagged the same *number* of adverse entities overall (19 each), but they didn't flag the same *entities*. Only 14 of the flags matched. 5 were caught only by the Hindi pipeline, and 5 only by the English-translated pipeline.

**About 42% of the unique adverse-entity findings across both runs would have been missed if only one pipeline had been used.**

That was the finding that surprised me most. On aggregate counts the two approaches look equivalent. When you look at the actual overlap, they're catching partly different things.

### Three examples of what "different things" means

**A single person, two spellings.** An article about the CGPSC recruitment scandal named a former commissioner as **टामन सिंह सोनवानी**. The Hindi pipeline transliterated him "Taman Singh Sonwani". The translate-first pipeline, after Google's own translation, called him "Toman Singh Sonwani". Same person, different spelling. In a real screening system these are two different entries in the sanctions database. One would match a watchlist. The other wouldn't.

**Different levels of granularity.** An article about corruption in a construction project in Raebareli was flagged by the Hindi pipeline as the *project* (`raebareli crematorium construction project`) and by the translate-first pipeline as the *administrator* (`raebareli district administration`). Both are correct, but they're pointing at different things. A compliance analyst reviewing only one output would miss half the picture.

**Same entity, different scripts.** A local corruption story in Chapra was flagged by the Hindi pipeline in Devanagari (`अध्यक्ष`, `अध्यक्ष के पति`) and by the translate-first pipeline in English ("Chairperson", "Husband of Chairperson"). Neither script alone lets you cross-reference a real database. You need both.

## What I think this means

The takeaway isn't that native Hindi screening is better. The takeaway is that the two approaches are **complementary rather than interchangeable**. A production system that only runs one is systematically missing the findings the other would have caught. The failure mode is almost always around how names and entities cross language boundaries.

The finding is small in scale. 15 articles is a sanity check, not a benchmark. But it's the right shape. Running the same test on 200 articles would sharpen the number without changing its direction.

## Limitations I want to be upfront about

**15 articles is a small sample.** The specific "42%" number will move with more data. What I have confidence in is the *pattern*, that meaningful entity-level disagreement exists between the two approaches.

**No human-labelled ground truth.** I don't know for certain that every flag was correct. I read every output myself and sanity-checked them against the articles, but a real evaluation would need a compliance analyst to label the data.

**Article bodies are short.** Google News RSS returns titles and summaries, not full articles. This is enough for headline-level screening but would miss risk mentioned deeper in a long piece. Most production adverse-media systems screen on headlines too, but this is worth naming.

**The classification is only as good as the prompt.** I iterated the prompt a few times but didn't formally test alternatives. A more rigorous version would.

**No entity resolution.** The pipeline doesn't yet know that "Taman Singh Sonwani" and "Toman Singh Sonwani" are the same person. Building that layer is the obvious next step, and it's the problem this benchmark was designed to motivate.

## How to run it

You need Python 3.10+ and a free Google AI Studio API key.

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1     # Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root with `GEMINI_API_KEY=your-key-here`.

Then:

```bash
python fetch_news.py       # test the news fetcher
python screener.py         # test the screener on a hardcoded sample
python run_screener.py     # fetch and screen recent articles
python benchmark.py        # run the native-vs-translate comparison
```

Results save to a local `results/` folder (git-ignored, since real names appear in the output).

## Files

- `fetch_news.py`: pulls Hindi articles from Google News RSS
- `screener.py`: sends an article to Gemini and returns structured JSON
- `run_screener.py`: end-to-end runner: fetch, screen, save
- `benchmark.py`: the comparison between native and translate-first
- `test_api.py`: smoke test for API setup

## A note on tooling

I built this using Google's Gemini API on the free tier. That was a deliberate choice. I wanted the pipeline to be reproducible by anyone without a credit card. Google shuffled available models several times during the build, so `screener.py` centralises the model name in one constant to make swaps painless. The benchmark also includes basic retry logic on rate-limit errors, because free-tier limits are tight enough that a 15-article run occasionally bumps into them.

## A note on how this was built

I built this using Claude (Anthropic) as an AI coding assistant. The design of the project, the choice of what to test, the interpretation of the results, and this write-up are mine. Claude helped me write the code and debug it. I'm being upfront about this because I think the honest version of "how a junior person builds a working RegTech prototype in 2026" is more useful than pretending otherwise.

---

Built by Gary Singh, Hong Kong