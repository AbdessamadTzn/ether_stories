import json
import asyncio
from pathlib import Path
from elevenlabs import AsyncElevenLabs
import config  # <- on importe le fichier config

# ----------------------------------------------------------------------
# 1. Config API (async)
# ----------------------------------------------------------------------
client = AsyncElevenLabs(api_key=config.API_KEY)
VOICE_ID = config.VOICE_ID

# ----------------------------------------------------------------------
# 2. Charger le JSON
# ----------------------------------------------------------------------
with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ----------------------------------------------------------------------
# 3. Fonction ASYNC pour générer l’audio d’un chapitre
# ----------------------------------------------------------------------
async def generate_chapter_audio(chapter):
    chapter_num = chapter["chapter_number"]
    chapter_title = chapter["title"]
    text = chapter["story_text"]
    out_path = Path("audio") / f"chapter_{chapter_num}.wav"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"--- Lancement Chapitre {chapter_num}: {chapter_title} ---")
    async with client.text_to_speech.with_raw_response.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id="eleven_flash_v2",
    ) as response:
        audio_bytes = b"".join([chunk async for chunk in response.data])
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
    print(f"Audio chapitre sauvegardé : {out_path}")

# ----------------------------------------------------------------------
# 4. Pipeline async pour tous les chapitres (PARALLÈLE)
# ----------------------------------------------------------------------
async def main():
    tasks = [asyncio.create_task(generate_chapter_audio(chapter)) for chapter in data["chapitres"]]
    await asyncio.gather(*tasks)
    print("\nTous les chapitres ont été synthétisés en parallèle !")

# ----------------------------------------------------------------------
# 5. Lancer asyncio
# ----------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
