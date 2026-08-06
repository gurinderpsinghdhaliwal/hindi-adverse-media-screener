import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents="Say hello in Hindi, then explain what adverse media screening means in one sentence."
)

print(response.text)