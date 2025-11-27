import os
import json
import re
import math
from typing import List, Optional, Dict, Any
from groq import Groq
from app.core.config import settings
from app.agents.context_loader import load_context, wrap_user_input, get_user_friendly_error

# Use settings for API Key
client = Groq(api_key=settings.GROQ_API_KEY)

# Load hardened system prompt from context file
SYSTEM_PROMPT = load_context("manager")


def calculate_chapter_count(duration_minutes: int) -> int:
    """Calculate the expected number of chapters based on duration.
    
    Rule: 1 chapter = 1-2 minutes, so chapters = ceil(duration / 2)
    Examples: 2min→1ch, 3min→2ch, 5min→3ch, 10min→5ch
    """
    return max(1, math.ceil(duration_minutes / 2))


def get_user_prompt(age, interests, peurs, keywords, moral, type_histoire, duree_minutes, personnage, transcription=None):
    """Build user prompt with input isolation (XML wrapped)."""
    
    # Calculate expected chapter count
    expected_chapters = calculate_chapter_count(duree_minutes)
    
    # Build the raw user data
    raw_input = f"""
Age de l'enfant: {age}
Intérêts: {interests}
Peurs à éviter: {peurs}
Mots-clés pour l'histoire: {keywords}
Morale souhaitée: {moral}
Type d'histoire: {type_histoire}
Durée souhaitée: {duree_minutes} minutes
Nombre de chapitres requis: {expected_chapters} (OBLIGATOIRE - ne pas modifier)
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
    
    duree_minutes = user_input.get("duree_minutes", 5)
    expected_chapters = calculate_chapter_count(duree_minutes)
    
    prompt = get_user_prompt(
        age=user_input.get("age", 6),
        interests=user_input.get("interests", []),
        peurs=user_input.get("peurs", []),
        keywords=kw_str,
        moral=user_input.get("moral", "Amitié"),
        type_histoire=user_input.get("type_histoire", "Aventure"),
        duree_minutes=duree_minutes,
        personnage=user_input.get("personnage", ""),
        transcription=transcription
    )
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
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
        
        # Validate and enforce chapter count
        if "chapitres" in plan:
            actual_chapters = len(plan["chapitres"])
            if actual_chapters != expected_chapters:
                # Log the discrepancy but adjust durations to match
                from app.core.logger import get_logger
                logger = get_logger(__name__)
                logger.warning(
                    f"Chapter count mismatch: expected {expected_chapters}, got {actual_chapters}. "
                    f"Duration: {duree_minutes}min"
                )
                
                # Redistribute time evenly across actual chapters
                time_per_chapter = duree_minutes / actual_chapters
                for chapter in plan["chapitres"]:
                    chapter["duree_minutes"] = round(time_per_chapter, 1)
        
        return {"plan": plan}
    except Exception as e:
        return {"error": f"Manager Error: {str(e)}"}
