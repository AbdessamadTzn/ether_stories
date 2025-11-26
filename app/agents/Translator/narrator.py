import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
from groq import Groq

# Charger le JSON
with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Forcer la langue de l'audio
langue_audio = "Français"

# 🔹 Concaténer tout le texte des chapitres
full_text = ""
for chapitre in data["chapitres"]:
    title = chapitre.get("title", "")
    story_text = chapitre.get("story_text", "")
    full_text += f"{title}\n\n{story_text}\n\n--- Chapitre suivant ---\n\n"

# Choix du modèle selon la langue
if langue_audio.lower() in ["français", "arabe"]:
    model = "playai-tts-arabic"
    voice = "Nasser-PlayAI"
else:
    model = "playai-tts"
    voice = "Arista-PlayAI"

print(f"Modèle choisi : {model} | Voix : {voice}")

# Nom du fichier audio unique
speech_file_path = "all_chapters.wav"

# TTS sur tout le texte concaténé
response = client.audio.speech.create(
    model=model,
    voice=voice,
    input=full_text,
    response_format="wav"
)

response.write_to_file(speech_file_path)
print(f"Audio généré pour tous les chapitres -> {speech_file_path}")
