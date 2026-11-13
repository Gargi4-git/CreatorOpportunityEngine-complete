import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in the .env file.")

client = genai.Client(api_key=api_key)


def generate_opportunity(prompt: str) -> str:
    """
    Send a prompt to Gemini and return the response.
    Uses flash-lite models with fallback for resilient generation.
    """
    models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-latest"]
    last_err = None

    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise last_err
    return ""


if __name__ == "__main__":
    prompt = """
    You are an AI content strategist.
    Give me one short content idea for students
    who want to learn practical machine learning.
    """
    result = generate_opportunity(prompt)
    print("\nGemini Response:")
    print("----------------")
    print(result)
