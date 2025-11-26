import os
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def generate_chapter_content(prompt: str) -> str:
    """
    Generates the text content for a chapter.
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un écrivain de contes pour enfants talentueux."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Writer Error: {str(e)}")
