"""
Prompts pour l'Agent Manager
Crée le plan complet de l'histoire avec tous les paramètres
"""
from typing import Optional

def get_system_prompt() -> str:
    return """Tu es un créateur d'histoires pour enfants expert. 

Tu dois TOUJOURS retourner un JSON VALIDE avec cette structure EXACTE (sans balises markdown, sans texte avant ou après):

{
  "plan": {
    "titre": "Le titre de l'histoire",
    "type_histoire": "aventure/conte/fantaisie/etc",
    "duree_estimee": 10,
    "age_cible": 7,
    "personnage_principal": "Description concise du personnage principal (2-3 phrases)"
  },
  "chapitres": [
    {
      "numero": 1,
      "titre": "Titre du chapitre",
      "resume": "Résumé CONCIS du chapitre en 3-4 phrases COURTES. Décris l'essentiel: situation initiale, action principale, et transition vers le suivant. Ce résumé sera développé plus tard par un autre agent.",
      "duree_minutes": 2
    }
  ],
  "morale": {
    "valeur_principale": "courage/amitié/respect/etc",
    "message": "Le message moral en 1-2 phrases",
    "integration": "Comment la morale est intégrée en 1-2 phrases"
  },
  "personnages": [
    {
      "nom": "Nom du personnage",
      "role": "principal/secondaire",
      "description": "Description concise en 1-2 phrases: apparence et rôle clé"
    }
  ],
  "elements_cles": {
    "keywords_utilises": ["mot1", "mot2"],
    "interets_integres": ["intérêt1", "intérêt2"],
    "peurs_evitees": ["peur1", "peur2"]
  }
}

RÈGLES CRITIQUES:
- Retourne UNIQUEMENT le JSON, RIEN d'autre
- PAS de texte explicatif avant ou après
- PAS de balises markdown (```json)
- Tous les champs doivent être présents
- Les valeurs numériques doivent être des nombres, pas des strings
- IMPORTANT: Chaque chapitre = 2 minutes EXACTEMENT (duree_minutes: 2)
- Le résumé de chaque chapitre doit faire 3-4 PHRASES COURTES maximum
- Garde les phrases simples et directes, un autre agent développera le contenu complet"""


def get_user_prompt(
    age: int,
    interests: list,
    peurs: list,
    keywords: str,
    moral: str,
    type_histoire: str,
    duree_minutes: int,
    personnage: str,
    transcription: Optional[str] = None,
    manager_decides: bool = True
) -> str:
    prompt = f"""Crée un plan d'histoire pour enfant avec ces paramètres:

PARAMÈTRES:
- Âge: {age} ans
- Type d'histoire: {type_histoire}
- Durée totale: {duree_minutes} minutes
- Nombre de chapitres: {duree_minutes // 2} chapitres (chaque chapitre = 2 minutes)
- Centres d'intérêt: {', '.join(interests) if interests else 'aucun'}
- Peurs à éviter: {', '.join(peurs) if peurs else 'aucune'}
- Morale souhaitée: {moral}
"""
    
    if transcription:
        prompt += f"\nTRANSCRIPTION AUDIO (SOURCE PRINCIPALE):\n{transcription}\n"
    
    if keywords:
        prompt += f"\nMOTS-CLÉS SUGGÉRÉS:\n{keywords}\n"
    
    if personnage:
        prompt += f"\nPERSONNAGE PRINCIPAL SOUHAITÉ: {personnage}\n"
    
    prompt += f"""
INSTRUCTIONS:
1. Utilise la TRANSCRIPTION comme source principale si disponible
2. Intègre les centres d'intérêt de l'enfant
3. ÉVITE absolument les peurs mentionnées
4. Crée EXACTEMENT {duree_minutes // 2} chapitres de 2 minutes chacun
5. Pour chaque chapitre, écris un résumé CONCIS de 3-4 phrases COURTES qui décrit:
   - La situation initiale du chapitre (1 phrase)
   - L'action ou événement principal (1-2 phrases)
   - La transition vers le chapitre suivant (1 phrase)
6. Garde les phrases simples et directes - un autre agent développera le contenu complet
7. Adapte le vocabulaire et la complexité à l'âge {age} ans
8. Intègre naturellement la morale "{moral}"

RAPPEL IMPORTANT: 
- Chaque chapitre = EXACTEMENT 2 minutes (duree_minutes: 2)
- Les résumés doivent être COURTS et CONCIS (3-4 phrases maximum)
- Évite les phrases trop longues ou trop détaillées
- Retourne UNIQUEMENT le JSON avec la structure exacte demandée, sans aucun texte supplémentaire."""
    
    return prompt