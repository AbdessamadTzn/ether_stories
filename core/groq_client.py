# core/groq_client.py

import os
from dotenv import load_dotenv
from groq import Groq

# Charger les variables d'environnement (.env)
load_dotenv()

# Récupération de la clé API GROQ
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY is missing in .env file")

# Initialisation du client Groq partagé par tous les agents
client = Groq(api_key=GROQ_API_KEY)
