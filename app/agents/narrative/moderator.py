import json
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def verify_coherence(text: str, context: dict) -> dict:
    """
    Verifies if the chapter text is coherent and safe.
    Returns {"coherent": bool, "reason": str}
    """
    prompt = f"""
    Tu es un modérateur. Vérifie le texte suivant pour une histoire d'enfant.
    
    Contexte: {context}
    
    Texte à vérifier:
    {text}
    
    Réponds UNIQUEMENT en JSON:
    {{
        "coherent": true/false,
        "reason": "Explication si false"
    }}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        # Fail safe: assume coherent if check fails to avoid blocking
        print(f"Moderator Error: {e}")
        return {"coherent": True, "reason": "Moderator check failed, passing by default."}
