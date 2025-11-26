import json
from groq import Groq
import os
import re
from dotenv import load_dotenv
from pathlib import Path

# try imports robustly (module vs script)
try:
    from ether_stories.app.agents.narrative_agent.painter import build_image_prompt, generer_image
except Exception:
    from agents.narrative_agent.painter import build_image_prompt, generer_image

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


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



def traduire_chapitre(chapter, langue_cible):
    title = chapter["title"]
    content = chapter["story_text"]
    number = chapter["chapter_number"]

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

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Tu es un traducteur professionnel pour histoires d'enfants."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    raw = completion.choices[0].message.content
    return extract_json(raw)


def _save_translated_image(chapter, trad: dict):
    prompt_obj = build_image_prompt(
        title=trad["chapter_header_translated"],
        summary=trad["chapter_content_translated"][:250],  # court résumé pour prompt
        characters=[c.get("nom") for c in chapter.get("characters", []) if isinstance(c, dict)],
        age=chapter.get("target_age", None),
        forbidden=chapter.get("forbidden_words", [])
    )
    out_dir = Path(__file__).resolve().parents[1] / "chapitres"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / f"chapter_{chapter['chapter_number']}_translated.png"
    generer_image(prompt_obj, img_path)
    return str(img_path)


if __name__ == "__main__":
    with open("output.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    chapitres = data["chapitres"]

    for chapter in chapitres:
        trad = traduire_chapitre(chapter, langue_cible="chinese")
        img_path = _save_translated_image(chapter, trad)

        print(f"\n===== Traduction du chapitre {chapter['chapter_number']} =====\n")

        print(trad["chapter_header_translated"])
        print()
        print(trad["chapter_content_translated"])
        print("\n--------------------------------------------\n")
