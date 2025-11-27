import json
from groq import Groq
from app.core.config import settings
from app.agents.context_loader import load_context, wrap_content_for_moderation, get_user_friendly_error

client = Groq(api_key=settings.GROQ_API_KEY)

# Load hardened system prompt from context file
SYSTEM_PROMPT = load_context("moderator")


def verify_coherence(text: str, context: dict) -> dict:
    """
    Verifies if the chapter text is coherent and safe for children.
    Uses hardened context with input isolation.
    
    Returns {"approved": bool, "safe_for_children": bool, "reason": str, "user_message": str}
    """
    # Wrap content in XML tags for input isolation
    wrapped_content, wrapped_context = wrap_content_for_moderation(text, context)
    
    prompt = f"""
{wrapped_content}

{wrapped_context}

Évalue ce contenu pour une histoire d'enfant.
Retourne UNIQUEMENT ce JSON:
{{
    "approved": true/false,
    "safe_for_children": true/false,
    "age_appropriate": true/false,
    "reason": "Explication si rejeté",
    "severity": "safe|mild_concern|rejected"
}}
"""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(completion.choices[0].message.content)
        
        # Add user-friendly message if rejected
        if not result.get("approved", True) or result.get("severity") == "rejected":
            result["user_message"] = get_user_friendly_error("MODERATION_FAILED")
        else:
            result["user_message"] = None
            
        # Map to legacy format for compatibility
        result["coherent"] = result.get("approved", True)
        
        return result
        
    except Exception as e:
        print(f"Moderator Error: {e}")
        # Fail CLOSED for security - reject on error
        return {
            "coherent": False,
            "approved": False,
            "safe_for_children": False,
            "reason": f"Moderation check failed: {str(e)}",
            "user_message": get_user_friendly_error("GENERATION_ERROR"),
            "severity": "rejected"
        }
