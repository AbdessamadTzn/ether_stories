import os
from pathlib import Path
from elevenlabs import ElevenLabs
from app.core.config import settings

# Voice IDs for different languages
VOICE_MAP = {
    "fr": "tKaoyJLW05zqV0tIH9FD",  # French voice
    "en": "KoVIHoyLDrQyd4pGalbs",  # English voice
    "zh": "hkfHEbBvdQFNX4uWHqRF",  # Chinese voice
}

# Default voice (French)
DEFAULT_VOICE = VOICE_MAP["fr"]

# Model
TTS_MODEL = "eleven_multilingual_v2"


def generate_audio(text: str, chapter_num: int, lang: str = "fr") -> str:
    """
    Generates audio from text using ElevenLabs.
    
    Args:
        text: The text to convert to speech
        chapter_num: Chapter number for filename
        lang: Language code (fr, en, zh)
    
    Returns:
        Relative path to audio file or empty string on error.
    """
    if not settings.ELEVENLABS_API_KEY:
        print("Warning: No ElevenLabs API Key. Skipping audio generation.")
        return ""
    
    # Get voice for language
    voice_id = VOICE_MAP.get(lang, DEFAULT_VOICE)
    
    client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
    
    try:
        audio_generator = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=TTS_MODEL
        )
        
        # Save to static/audio
        output_dir = Path("app/static/audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Include language in filename
        filename = f"chapter_{chapter_num}_{lang}_{os.urandom(4).hex()}.mp3"
        file_path = output_dir / filename
        
        with open(file_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
        
        print(f"Audio generated: {filename} (lang={lang}, voice={voice_id})")
        return f"/static/audio/{filename}"
        
    except Exception as e:
        print(f"Narrator Error: {e}")
        return ""


def generate_audio_for_translation(text: str, chapter_id: int, lang: str) -> str:
    """
    Generates audio for a translated chapter.
    Used for on-demand audio generation when user requests it.
    
    Args:
        text: The translated text
        chapter_id: Database chapter ID
        lang: Language code (en, zh)
    
    Returns:
        Relative path to audio file or empty string on error.
    """
    if lang not in VOICE_MAP:
        print(f"Unsupported language for TTS: {lang}")
        return ""
    
    return generate_audio(text, chapter_id, lang)
