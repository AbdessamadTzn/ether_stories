import os
import json
import re
from typing import List, Optional, Dict, Any
from groq import Groq
from app.core.config import settings
from app.agents.context_loader import load_context, wrap_user_input, get_user_friendly_error

# Use settings for API Key
client = Groq(api_key=settings.GROQ_API_KEY)

# Load hardened system prompt from context file
SYSTEM_PROMPT = load_context("manager")


def get_user_prompt(age, interests, peurs, keywords, moral, type_histoire, duree_minutes, personnage, transcription=None):
    """Build user prompt with input isolation (XML wrapped)."""
    
    # Build the raw user data
    raw_input = f"""
Age de l'enfant: {age}
Intérêts: {interests}
Peurs à éviter: {peurs}
Mots-clés pour l'histoire: {keywords}
Morale souhaitée: {moral}
Type d'histoire: {type_histoire}
Durée souhaitée: {duree_minutes} minutes
Personnage principal: {personnage}
"""
    if transcription:
        raw_input += f"Transcription audio de l'enfant: {transcription}\n"
    
    # Wrap in XML tags for input isolation
    wrapped_input = wrap_user_input(raw_input)
    
    prompt = f"""
{wrapped_input}

Analyse les données ci-dessus et crée un plan d'histoire.
Retourne UNIQUEMENT le JSON suivant (pas de texte avant ou après):
{{
  "plan": {{"titre": "...", "type_histoire": "...", "duree_estimee": number, "age_cible": number, "personnage_principal": "..."}},
  "chapitres": [{{"numero": 1, "titre": "...", "resume": "...", "duree_minutes": number}}],
  "morale": {{"valeur_principale": "...", "message": "...", "integration": "..."}},
  "personnages": [{{"nom": "...", "role": "...", "description": "..."}}],
  "elements_cles": {{"keywords_utilises": [], "interets_integres": [], "peurs_evitees": []}}
}}
"""
    return prompt

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
        
        # Check if LLM returned an error response (content rejected)
        if plan.get("error") == True:
            user_message = plan.get("message", "Ce thème n'est pas adapté pour une histoire pour enfants.")
            return {"error": user_message}
        
        return {"plan": plan}
    except Exception as e:
        return {"error": f"Manager Error: {str(e)}"}
