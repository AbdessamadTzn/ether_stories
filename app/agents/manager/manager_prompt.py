"""
Prompts pour l'Agent Manager
Crée le plan complet de l'histoire avec tous les paramètres
"""

def get_system_prompt() -> str:
    """
    Prompt système pour l'Agent Manager
    
    Returns:
        Prompt système détaillé
    """
    return """Tu es l'Agent Manager, le chef d'orchestre de la création d'histoires pour enfants.

🎯 TON RÔLE:
Créer un PLAN DÉTAILLÉ et STRUCTURÉ d'une histoire personnalisée pour un enfant spécifique.
Tu dois prendre en compte TOUS les paramètres fournis (âge, centres d'intérêt, peurs, etc.).

📋 TU GÉNÈRES:
1. Plan de l'histoire (structure narrative complète)
2. Liste des chapitres (avec titres accrocheurs)
3. Résumé détaillé de chaque chapitre
4. Morale intégrée naturellement

🎨 PRINCIPES CRÉATIFS:
- Adapter le vocabulaire à l'âge de l'enfant
- Intégrer les centres d'intérêt de manière cohérente
- Éviter les éléments qui correspondent aux peurs de l'enfant
- Respecter le type d'histoire demandé (aventure, fantaisie, etc.)
- Adapter la longueur selon le temps demandé
- Inclure le personnage principal demandé

⚠️ GESTION DES PEURS:
Si l'enfant a des peurs (noir, monstres, etc.), tu dois:
- NE PAS inclure ces éléments comme menaces
- Transformer ces peurs en éléments positifs si mentionnés
- Créer un environnement rassurant et positif

📤 FORMAT DE SORTIE (JSON STRICT):
{{
  "plan": {{
    "titre": "Le Titre Magique de l'Histoire",
    "type_histoire": "aventure/fantaisie/conte/science-fiction",
    "duree_estimee": 10,
    "age_cible": 7,
    "personnage_principal": "Nom et description du personnage"
  }},
  "chapitres": [
    {{
      "numero": 1,
      "titre": "Titre du chapitre 1",
      "resume": "Résumé détaillé (5-6 phrases)",
      "duree_minutes": 3
    }},
    {{
      "numero": 2,
      "titre": "Titre du chapitre 2",
      "resume": "Résumé détaillé (5-6 phrases)",
      "duree_minutes": 4
    }},
    {{
      "numero": 3,
      "titre": "Titre du chapitre 3",
      "resume": "Résumé détaillé (5-6 phrases)",
      "duree_minutes": 3
    }}
  ],
  "morale": {{
    "valeur_principale": "courage/amitié/persévérance/etc.",
    "message": "La morale explicite de l'histoire",
    "integration": "Comment elle sera transmise dans le récit"
  }},
  "personnages": [
    {{
      "nom": "Nom du personnage",
      "role": "principal/secondaire",
      "description": "Description physique et traits de caractère"
    }}
  ],
  "elements_cles": {{
    "keywords_utilises": ["keyword1", "keyword2"],
    "interets_integres": ["interet1", "interet2"],
    "peurs_evitees": ["peur1", "peur2"]
  }}
}}

⚠️ IMPORTANT: Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""


def get_user_prompt(
    age: int,
    interests: list,
    peurs: list,
    keywords: str,
    moral: str,
    type_histoire: str,
    duree_minutes: int,
    personnage: str
) -> str:
    """
    Construire le prompt utilisateur avec tous les paramètres
    
    Args:
        age: Âge de l'enfant
        interests: Liste des centres d'intérêt
        peurs: Liste des peurs à éviter
        keywords: Mots-clés pour l'histoire
        moral: Morale souhaitée
        type_histoire: Type d'histoire (aventure, conte, etc.)
        duree_minutes: Durée souhaitée en minutes
        personnage: Personnage principal souhaité
    
    Returns:
        Prompt utilisateur complet
    """
    
    # Adaptation selon l'âge
    age_guidance = ""
    if age <= 5:
        age_guidance = """
ÂGE 3-5 ANS:
- Vocabulaire très simple
- Phrases courtes (5-8 mots)
- Concepts concrets uniquement
- Histoire rassurante et prévisible
- Répétitions pour mémorisation
- Fin très heureuse et claire
"""
    elif age <= 8:
        age_guidance = """
ÂGE 6-8 ANS:
- Vocabulaire accessible avec mots nouveaux
- Phrases de longueur moyenne
- Introduction de concepts simples
- Péripéties et rebondissements
- Humour léger bienvenu
- Résolution positive avec leçon
"""
    else:
        age_guidance = """
ÂGE 9-12 ANS:
- Vocabulaire enrichi et varié
- Phrases complexes possibles
- Concepts abstraits acceptables
- Intrigues plus élaborées
- Suspense et mystère possibles
- Nuances dans la morale
"""
    
    # Formatage des listes
    interests_str = ", ".join(interests) if interests else "aucun spécifié"
    peurs_str = ", ".join(peurs) if peurs else "aucune"
    
    # Calcul du nombre de chapitres suggéré
    nb_chapitres = max(2, min(5, duree_minutes // 3))
    
    prompt = f"""Crée un plan d'histoire complet pour un enfant avec ces paramètres:

👤 PROFIL DE L'ENFANT:
- Âge: {age} ans
- Centres d'intérêt: {interests_str}
- Peurs à ÉVITER: {peurs_str}

{age_guidance}

📖 PARAMÈTRES DE L'HISTOIRE:
- Mots-clés à intégrer: {keywords}
- Morale souhaitée: {moral}
- Type d'histoire: {type_histoire}
- Durée totale: {duree_minutes} minutes (environ {nb_chapitres} chapitres)
- Personnage principal: {personnage}

📋 CONSIGNES SPÉCIFIQUES:
1. Crée {nb_chapitres} chapitres d'environ {duree_minutes // nb_chapitres} minutes chacun
2. Intègre TOUS les mots-clés de manière naturelle: {keywords}
3. Base le personnage principal sur: {personnage}
4. Assure-toi que le type "{type_histoire}" est respecté
5. Intègre les centres d'intérêt: {interests_str}
6. ÉVITE ABSOLUMENT ces éléments (peurs de l'enfant): {peurs_str}
7. La morale "{moral}" doit être naturellement intégrée

🎯 OBJECTIF:
Créer une histoire captivante, adaptée à l'âge, qui respecte tous les paramètres,
évite les peurs de l'enfant, et transmet la morale de façon positive.

Réponds UNIQUEMENT avec le JSON demandé dans le format spécifié."""
    
    return prompt