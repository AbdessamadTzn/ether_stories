"""
Agent S2T (Speech-to-Text)
Transcrit l'audio de l'enfant en mots-clés JSON
Fichier adapté pour fonctionner sans GroqConfig : configuration locale et client Groq par agent.
"""
from typing import Optional
import json
import os
import re
from groq import Groq
from dotenv import load_dotenv

# Prompt helper
try:
    from .speech_to_text_prompt import get_transcription_prompt, get_post_processing_instructions
except Exception:
    try:
        from speech_to_text_prompt import get_transcription_prompt, get_post_processing_instructions
    except Exception:
        # Si le fichier de prompts n'est pas encore prêt, on fallback sur un prompt simple
        def get_transcription_prompt() -> str:
            return (
                "Transcris l'audio d'un enfant en mots-clés et phrase complète. "
                "Corrige les erreurs évidentes, conserve le langage enfantin."
            )
        def get_post_processing_instructions() -> str:
            return "Renvoie une transcription claire et des mots-clés séparés par des virgules."

load_dotenv()

# Configuration locale (peut être override via .env)
DEFAULT_MODEL = os.getenv("S2T_MODEL", "whisper-large-v3")
DEFAULT_LANGUAGE = os.getenv("S2T_LANGUAGE", "fr")
DEFAULT_TEMPERATURE = float(os.getenv("S2T_TEMPERATURE", "0.0"))

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("GROQ_API_KEY is required in environment for S2TAgent")

class S2TAgent:
    """
    Agent Speech-to-Text avec Whisper (ou autre modèle configuré).
    INPUT: Fichier audio (bytes ou path)
    OUTPUT: dict {
        "success": bool,
        "keywords": str,
        "transcription_raw": str,
        "confidence": "high/medium/low",
        "language": str
    }
    """
    def __init__(self):
        self.name = "Agent S2T"
        self.model = DEFAULT_MODEL
        self.params = {"temperature": DEFAULT_TEMPERATURE}
        self.client = Groq(api_key=API_KEY)
        print(f"✅ {self.name} initialisé | modèle: {self.model}")

    def transcribe_audio(
        self,
        audio_file,
        language: str = DEFAULT_LANGUAGE,
        extract_keywords: bool = True
    ) -> dict:
        """
        Transcrit l'audio et retourne un dict structuré.
        - audio_file peut être :
          - un chemin vers un fichier (str/Path)
          - un objet bytes
          - un file-like object (avec .read())
        """
        try:
            # Préparer le flux d'upload
            file_param = None
            if isinstance(audio_file, (str, os.PathLike)):
                file_param = open(str(audio_file), "rb")
            elif isinstance(audio_file, (bytes, bytearray)):
                file_param = audio_file
            elif hasattr(audio_file, "read"):
                file_param = audio_file
            else:
                raise ValueError("audio_file must be a path, bytes, or file-like object")

            # Prompt de contexte facultatif pour améliorer la transcription
            prompt = get_transcription_prompt()

            # Appel au client Groq (Whisper / speech-to-text)
            resp = self.client.audio.transcriptions.create(
                file=file_param,
                model=self.model,
                language=language,
                prompt=prompt,
                response_format="json",
                temperature=self.params.get("temperature", 0.0),
            )

            # Extraire la transcription du résultat
            raw_text = ""
            if hasattr(resp, "text"):
                raw_text = resp.text or ""
            elif isinstance(resp, dict):
                raw_text = resp.get("text", "") or resp.get("transcription", "") or ""
            elif getattr(resp, "choices", None):
                try:
                    raw_text = resp.choices[0].message.content
                except Exception:
                    raw_text = str(resp)
            else:
                raw_text = str(resp)

            raw_text = raw_text.strip()

            keywords = ""
            if extract_keywords:
                keywords = self._extract_keywords(raw_text)
            else:
                keywords = raw_text

            confidence = self._evaluate_confidence(raw_text)

            return {
                "success": True,
                "keywords": keywords,
                "transcription_raw": raw_text,
                "confidence": confidence,
                "language": language,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "keywords": "",
                "transcription_raw": "",
                "confidence": "error",
                "language": language
            }
        finally:
            # Si on a ouvert un fichier en local, on ferme
            try:
                if isinstance(audio_file, (str, os.PathLike)) and 'file_param' in locals() and hasattr(file_param, "close"):
                    file_param.close()
            except Exception:
                pass

    def _extract_keywords(self, text: str) -> str:
        """
        Extraction basique de mots-clés depuis la transcription.
        - Nettoyage des "euh", "hmm"
        - Découpage par ponctuation
        - Heuristique simple : fréquence et longueur minimale
        """
        if not text:
            return ""

        text_clean = text.lower()
        # supprime interjections
        fillers = ["euh", "hmm", "ben", "voilà", "heu", "alors", "oui", "non"]
        for f in fillers:
            text_clean = text_clean.replace(f, " ")

        # garder phrases, mais extraire tokens signifiants
        tokens = re.split(r"[^\wàâéèêëîïôùûüç'-]+", text_clean)
        tokens = [t.strip().strip("-'") for t in tokens if t and len(t) >= 3]
        # compter fréquence
        freq = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        # ordre par fréquence
        sorted_tokens = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
        keywords = ", ".join([kv[0] for kv in sorted_tokens[:8]])
        return keywords

    def _evaluate_confidence(self, text: str) -> str:
        """
        Heuristique simple : longueur du texte -> confiance
        """
        if not text:
            return "low"
        length = len(text.strip())
        if length < 10:
            return "low"
        if length < 60:
            return "medium"
        return "high"

    def transcribe_to_json(self, audio_file) -> str:
        result = self.transcribe_audio(audio_file)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def transcribe_and_create_story(
        self,
        audio_file,
        age: int = 7,
        interests: list = None,
        peurs: list = None,
        moral: str = "courage et amitié",
        type_histoire: str = "aventure",
        duree_minutes: int = 10,
        personnage: str = "",
        nom_enfant: Optional[str] = None,
        manager_decides: bool = True  # <-- nouveau param: le Manager décide
    ) -> dict:
        """
        Transcrit l'audio ET crée automatiquement le plan d'histoire.
        Si manager_decides=True, le Manager recevra la transcription brute et choisira mots-clés / personnage.
        """
        # Import du Manager (lazy import pour éviter les dépendances circulaires)
        try:
            # Essayer import relatif (quand dans un package)
            from ..manager.manager import manager_agent
        except (ImportError, ValueError):
            try:
                # Essayer import absolu depuis agents
                from agents.manager.manager import manager_agent
            except ImportError:
                try:
                    # Essayer import direct (si dans le même dossier ou PYTHONPATH)
                    from manager import manager_agent
                except ImportError:
                    raise ImportError(
                        "Impossible d'importer manager_agent. "
                        "Vérifiez que manager.py est accessible dans:\n"
                        "- agents/manager/manager.py (import relatif)\n"
                        "- ou via PYTHONPATH"
                    )
        
        transcription_result = self.transcribe_audio(audio_file)
        
        if not transcription_result["success"]:
            return {
                "success": False,
                "error": f"Échec de la transcription: {transcription_result.get('error', 'Erreur inconnue')}",
                "transcription": transcription_result,
                "story_plan": None
            }
        
        keywords = transcription_result["keywords"]
        raw_text = transcription_result["transcription_raw"]

        # si on veut laisser le Manager décider, on ne force pas le personnage ici
        if not manager_decides:
            # fallback auto-personnage si l'utilisateur n'a rien fourni
            if not personnage and keywords:
                first_keyword = keywords.split(",")[0].strip()
                personnage = first_keyword

        # Appel du Manager en incluant la transcription brute
        story_plan = manager_agent.create_story_plan(
            age=age,
            interests=interests or [],
            peurs=peurs or [],
            keywords=keywords,
            moral=moral,
            type_histoire=type_histoire,
            duree_minutes=duree_minutes,
            personnage=personnage,
            nom_enfant=nom_enfant,
            transcription_raw=raw_text,   # <-- transcription brute passée au Manager
            manager_decides=manager_decides  # <-- si nécessaire
        )
        
        return {
            "success": True,
            "transcription": transcription_result,
            "story_plan": story_plan
        }

# Instance globale exportée (structure uniforme avec les autres agents)
s2t_agent = S2TAgent()