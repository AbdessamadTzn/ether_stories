import os
from pathlib import Path
from elevenlabs import ElevenLabs
from app.core.config import settings

def generate_audio(text: str, chapter_num: int) -> str:
    """
    Generates audio from text using ElevenLabs.
    Returns relative path to audio file.
    """
    if not settings.ELEVENLABS_API_KEY:
        print("Warning: No ElevenLabs API Key. Skipping audio generation.")
        return ""
        
    client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
    
    try:
        audio_generator = client.text_to_speech.convert(
            text=text,
            voice_id="21m00Tcm4TlvDq8ikWAM", # Rachel
            model_id="eleven_multilingual_v2"
        )
        
        # Save to static/audio
        output_dir = Path("app/static/audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"chapter_{chapter_num}_{os.urandom(4).hex()}.mp3"
        file_path = output_dir / filename
        
        with open(file_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
                
        return f"/static/audio/{filename}"
        
    except Exception as e:
        print(f"Narrator Error: {e}")
        return ""
