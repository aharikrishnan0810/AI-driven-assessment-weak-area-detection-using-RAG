import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

client = genai.Client(api_key=api_key)
EMBED_MODEL = "models/text-embedding-004"

def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = []
    batch_size = 100  # max allowed by Gemini API
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        response = client.models.embed_content(
            model=EMBED_MODEL,
            contents=batch
        )
        # Correct access for current Gemini client
        embeddings.extend([e.values for e in response.embeddings])
    return embeddings