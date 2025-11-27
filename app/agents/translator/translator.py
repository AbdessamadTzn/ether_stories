import json
import re
from groq import Groq
from app.core.config import settings
from typing import Dict
from app.agents.context_loader import load_context

client = Groq(api_key=settings.GROQ_API_KEY)

# Load hardened system prompt from context file
SYSTEM_PROMPT = load_context("translator")


def extract_json(raw):
    """
    Extrait un JSON propre depuis une réponse LLM.
    Nettoie :
    - Markdown
    - caractères invisibles RTL 
    - parasites unicode
    - espaces inutiles
    Fonctionne pour toutes les langues.
    """
    if raw is None:
        raise ValueError("Réponse vide du modèle.")

    # Nettoyage Markdown
    raw = raw.replace("```json", "").replace("```", "")

    # Nettoyage caractères invisibles RTL
    rtl_chars = ["\u202b", "\u202e", "\u202a", "\u200f", "\u200e"]
    for c in rtl_chars:
        raw = raw.replace(c, "")

    raw = raw.strip()

    # Extraction JSON
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        print("\n--- RAW OUTPUT (pas de JSON détecté) ---\n")
        print(raw)
        raise ValueError("Impossible d'extraire un JSON valide.")

    json_clean = match.group(0)

    try:
        return json.loads(json_clean)
    except json.JSONDecodeError as e:
        print("\n--- JSON INVALID ---\n", json_clean)
        raise e



def traduire_chapitre(chapter_number: int, title: str, content: str, langue_cible: str) -> Dict[str, str]:
    """
    Translate a chapter to the target language.
    
    Args:
        chapter_number: Chapter number
        title: Chapter title
        content: Chapter content text
        langue_cible: Target language (e.g., 'Arabic', 'Chinese', 'Spanish')
    
    Returns:
        Dictionary with translated header and content
    """
    number = chapter_number

    prompt = f"""
Tu es l’agent traducteur du pipeline multi-agents.

Ton rôle est de traduire proprement le chapitre en {langue_cible} :
- créer un en-tête littéraire : <mot pour Chapitre> <numéro> – <titre traduit>
- traduire fidèlement tout le contenu narratif

RÈGLES :
- Ne traduire aucun prénom.
- Ne rien ajouter ni retirer.
- Ne pas insérer de markdown.
- Ne pas inclure de texte hors JSON.
- Utiliser un JSON UTF-8 strict.
- Le texte arabe doit être renvoyé sans caractères invisibles RTL.

Données à traduire :

NUMÉRO : {number}
TITRE : {title}
CONTENU : {content}

Réponds UNIQUEMENT avec ce JSON :

{{
  "chapter_header_translated": "",
  "chapter_content_translated": ""
}}
"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional translator for children's stories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )

        raw = completion.choices[0].message.content
        result = extract_json(raw)
        
        # Map from French keys to standardized format
        translated_title = result.get("chapter_header_translated", result.get("translated_title", title))
        translated_content = result.get("chapter_content_translated", result.get("translated_content", content))
        
        return {
            "translated_title": translated_title,
            "translated_content": translated_content
        }
    except Exception as e:
        print(f"Translation error for chapter {number}: {e}")
        # Return original text if translation fails
        return {
            "translated_title": title,
            "translated_content": content
        }


# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ar": "Arabic",
    "zh": "Chinese",
    "es": "Spanish",
    "de": "German",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "it": "Italian"
}

def get_language_name(lang_code: str) -> str:
    """Get full language name from code"""
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code.title())