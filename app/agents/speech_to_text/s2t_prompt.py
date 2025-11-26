"""
Prompts pour l'Agent S2T (Speech-to-Text)
Transcription audio des mots-clés de l'enfant
"""

def get_transcription_prompt() -> str:
    """
    Prompt pour améliorer la transcription
    Whisper peut avoir besoin de contexte
    
    Returns:
        Prompt de transcription
    """
    return """Tu transcris l'audio d'un enfant qui parle de mots-clés pour créer une histoire.

CONTEXTE:
- L'enfant peut parler de personnages (dragon, princesse, pirate, etc.)
- L'enfant peut mentionner des lieux (château, forêt, océan, etc.)
- L'enfant peut décrire des objets (trésor, épée magique, baguette, etc.)
- L'enfant peut exprimer des émotions ou valeurs (courage, amitié, peur, etc.)

INSTRUCTIONS:
1. Transcris fidèlement ce que l'enfant dit
2. Corrige les erreurs grammaticales évidentes
3. Sépare les mots-clés par des virgules si possible
4. Garde le langage enfantin et naturel

EXEMPLE:
Audio: "euh... je veux un dragon... et une princesse... dans un château magique"
Transcription: "dragon, princesse, château magique"
"""

def get_post_processing_instructions() -> str:
    """
    Instructions pour le post-traitement de la transcription
    
    Returns:
        Instructions de nettoyage
    """
    return """NETTOYAGE DE LA TRANSCRIPTION:
1. Supprimer les hésitations (euh, hmm, ben, etc.)
2. Retirer les mots de remplissage (voilà, alors, etc.)
3. Extraire uniquement les mots-clés pertinents
4. Formater en liste séparée par des virgules
5. Garder la simplicité du langage enfantin

MOTS-CLÉS À PRIORISER:
- Personnages: dragon, princesse, pirate, chevalier, sorcière, fée, robot, dinosaure
- Lieux: château, forêt, océan, montagne, île, grotte, village
- Objets: trésor, épée, baguette, couronne, bateau, vaisseau
- Thèmes: aventure, amitié, magie, courage, mystère
"""