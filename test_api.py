import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Candidates in order of preference (higher-quota / more stable first)
CANDIDATES = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
]

for model in CANDIDATES:
    try:
        r = client.models.generate_content(
            model=model,
            contents="Say 'hello' in Hindi in one word.",
        )
        print(f"✓ {model} WORKS")
        print(f"  Response: {r.text.strip()}")
        print(f"\n  --> Use MODEL = \"{model}\" in your code")
        break
    except Exception as e:
        err = str(e)[:120]
        print(f"✗ {model}: {err}")