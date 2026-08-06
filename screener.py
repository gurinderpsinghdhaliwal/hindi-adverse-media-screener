"""
Hindi-Native Adverse Media Screener — v1
Screens Hindi-language text for adverse media indicators without translation.
"""
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-flash-latest"

# The prompt is the whole product. This is the piece to iterate on.
SYSTEM_PROMPT = """You are an AML/KYC compliance analyst screening Hindi-language news articles for adverse media indicators.

Read the article in the original Hindi. Do NOT translate it. Analyse it in-language.

For each named person or entity in the article, determine whether the article carries adverse media risk. Adverse media risk categories:
- FRAUD: financial fraud, embezzlement, misappropriation
- MONEY_LAUNDERING: money laundering, hawala, tax evasion, undisclosed assets
- SANCTIONS: sanctions violations, dealings with sanctioned parties
- CORRUPTION: bribery, kickbacks, political corruption
- TERRORISM_FINANCING: terrorism financing, links to designated groups
- ORGANISED_CRIME: organised crime, trafficking, extortion
- REGULATORY: regulatory action, SEBI/RBI/ED enforcement, arrests, charges
- LITIGATION: civil or criminal litigation with financial-crime nexus
- NONE: no adverse indicator

Return STRICT JSON matching this schema, with no prose before or after:
{
  "entities": [
    {
      "name": "entity name as it appears in the article",
      "name_devanagari": "name in original script if present, else null",
      "risk_category": "one of the categories above",
      "risk_severity": "HIGH | MEDIUM | LOW | NONE",
      "sentiment_score": -1.0 to 1.0 (negative = adverse),
      "supporting_quote_hindi": "short direct quote from the article that supports your classification",
      "reasoning": "one sentence in English explaining the classification"
    }
  ],
  "article_summary_english": "two-sentence English summary of the article for the compliance analyst"
}

If no named entities appear, return {"entities": [], "article_summary_english": "..."}."""


def screen_article(article_text: str, source_url: str = "") -> dict:
    """Send a Hindi article to Gemini and get back structured adverse-media JSON."""
    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.1,
        ),
        contents=f"Article source: {source_url}\n\nArticle text:\n{article_text}",
    )
    return json.loads(response.text)


# --- v1 test: one hardcoded article ---
if __name__ == "__main__":
    sample = """नई दिल्ली: प्रवर्तन निदेशालय (ईडी) ने एक बड़ी कार्रवाई करते हुए मुंबई के व्यवसायी राजेश शर्मा को धन शोधन के आरोप में गिरफ्तार किया है। ईडी के अनुसार, शर्मा ने फर्जी कंपनियों के जरिए लगभग 500 करोड़ रुपये का हवाला के माध्यम से विदेश भेजा। उनकी कंपनी शर्मा एक्सपोर्ट्स लिमिटेड पर सेबी ने भी जांच शुरू कर दी है। शर्मा को विशेष न्यायालय में पेश किया गया, जहां से उन्हें 14 दिन की न्यायिक हिरासत में भेज दिया गया।"""

    result = screen_article(sample, source_url="test://hardcoded-sample")
    print(json.dumps(result, indent=2, ensure_ascii=False))