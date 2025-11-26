import os
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def transcribe_audio(audio_file_path: str) -> dict:
    """
    Transcribes audio file to text using Groq Whisper.
    """
    try:
        with open(audio_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), file.read()),
                model="whisper-large-v3",
                response_format="json"
            )
            return {"text": transcription.text}
    except Exception as e:
        return {"error": str(e)}
