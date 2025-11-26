import os
import json
import re
from typing import List, Optional, Dict, Any
from groq import Groq
from app.core.config import settings

# Use settings for API Key
client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """
Tu es le "Manager Agent" pour Ether Stories.
Ton rôle est de créer un plan d'histoire structuré pour enfants.
Tu dois respecter scrupuleusement le format JSON demandé.
"""

def get_user_prompt(age, interests, peurs, keywords, moral, type_histoire, duree_minutes, personnage, transcription=None):
    base = f"""
    Crée un plan pour une histoire d'enfant.
    Age: {age}
    Intérêts: {interests}
    Peurs à éviter: {peurs}
    Mots-clés: {keywords}
    Morale: {moral}
    Type: {type_histoire}
    Durée: {duree_minutes} minutes
    Personnage principal: {personnage}
    """
    if transcription:
        base += f"\nBasé sur cette transcription audio de l'enfant: {transcription}"
        
    base += """
    Format de sortie attendu (JSON pur):
    {
      "plan": {"titre": "...", "type_histoire": "...", "duree_estimee": 10, "age_cible": 7, "personnage_principal": "..."},
      "chapitres": [{"numero": 1, "titre": "...", "resume": "...", "duree_minutes": 3}],
      "morale": {"valeur_principale": "...", "message": "...", "integration": "..."},
      "personnages": [{"nom": "...", "role": "...", "description": "..."}],
      "elements_cles": {"keywords_utilises": [], "interets_integres": [], "peurs_evitees": []}
    }
    """
    return base

def create_story_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates the story plan based on user input in state.
    """
    user_input = state.get("user_input", {})
    transcription = state.get("transcription")
    keywords = state.get("keywords", [])
    
    # Merge keywords if present
    kw_str = ", ".join(keywords) if keywords else user_input.get("keywords", "")
    
    prompt = get_user_prompt(
        age=user_input.get("age", 6),
        interests=user_input.get("interests", []),
        peurs=user_input.get("peurs", []),
        keywords=kw_str,
        moral=user_input.get("moral", "Amitié"),
        type_histoire=user_input.get("type_histoire", "Aventure"),
        duree_minutes=user_input.get("duree_minutes", 5),
        personnage=user_input.get("personnage", ""),
        transcription=transcription
    )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
        plan = json.loads(content)
        return {"plan": plan}
    except Exception as e:
        return {"error": f"Manager Error: {str(e)}"}
