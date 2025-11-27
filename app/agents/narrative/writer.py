import os
from groq import Groq
from app.core.config import settings
from app.agents.context_loader import load_context, wrap_chapter_instructions, get_user_friendly_error

client = Groq(api_key=settings.GROQ_API_KEY)

# Load hardened system prompt from context file
SYSTEM_PROMPT = load_context("writer")


def generate_chapter_content(prompt: str, context: str = "") -> str:
    """
    Generates the text content for a chapter.
    Uses hardened context with input isolation.
    
    Args:
        prompt: Chapter writing instructions
        context: Story context for continuity
    
    Returns:
        Generated chapter text or error marker
    """
    # Wrap inputs in XML tags for input isolation
    wrapped_instructions, wrapped_context = wrap_chapter_instructions(prompt, context)
    
    full_prompt = f"""
{wrapped_instructions}

{wrapped_context}

Écris le contenu du chapitre en français, adapté aux enfants.
Retourne UNIQUEMENT le texte narratif (pas de JSON, pas de markdown).
"""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        content = completion.choices[0].message.content
        
        # Check for error marker from the AI
        if "[ERREUR_CONTENU]" in content:
            raise RuntimeError(get_user_friendly_error("CONTENT_REJECTED"))
        
        return content
        
    except Exception as e:
        raise RuntimeError(f"Writer Error: {str(e)}")
