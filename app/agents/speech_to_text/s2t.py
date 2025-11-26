"""
Agent S2T (Speech-to-Text)
Transcrit l'audio de l'enfant en mots-clés JSON
"""
import json
from typing import Optional
import get_transcription_prompt, get_post_processing_instructions

class S2TAgent:
    """
    Agent Speech-to-Text avec Whisper
    
    INPUT: Fichier audio (bytes)
    OUTPUT: JSON {
        "keywords": "dragon, princesse, château",
        "transcription_raw": "transcription brute",
        "confidence": "high/medium/low"
    }
    """
    
    def __init__(self):
        self.name = "Agent S2T"
        self.model = GroqConfig.get_model("s2t")
        self.params = GroqConfig.get_params("s2t")
        self.client = GroqConfig.get_client()
        
        print(f"✅ {self.name} initialisé")
        print(f"   Modèle: {self.model}")
    
    def transcribe_audio(
        self,
        audio_file,
        language: str = "fr",
        extract_keywords: bool = True
    ) -> dict:
        """
        Transcrire un fichier audio en texte
        
        Args:
            audio_file: Fichier audio (UploadFile ou bytes)
            language: Code langue (fr, en, etc.)
            extract_keywords: Si True, extrait les mots-clés
        
        Returns:
            dict {
                "success": bool,
                "keywords": str,
                "transcription_raw": str,
                "confidence": str,
                "language": str
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"🎤 {self.name} - Transcription audio")
            print(f"{'='*60}")
            print(f"🌍 Langue: {language}")
            
            # Transcrire avec Whisper
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=language,
                response_format="json",
                temperature=self.params["temperature"]
            )
            
            raw_text = transcription.text
            print(f"📝 Transcription brute: {raw_text}")
            
            # Extraire les mots-clés si demandé
            if extract_keywords:
                keywords = self._extract_keywords(raw_text)
            else:
                keywords = raw_text
            
            # Évaluer la confiance (basé sur la longueur et cohérence)
            confidence = self._evaluate_confidence(raw_text)
            
            result = {
                "success": True,
                "keywords": keywords,
                "transcription_raw": raw_text,
                "confidence": confidence,
                "language": language
            }
            
            print(f"✅ Mots-clés extraits: {keywords}")
            print(f"📊 Confiance: {confidence}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            error_msg = f"Erreur transcription: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "keywords": "",
                "transcription_raw": "",
                "confidence": "error"
            }
    
    def _extract_keywords(self, text: str) -> str:
        """
        Extraire les mots-clés pertinents du texte
        
        Args:
            text: Transcription brute
        
        Returns:
            Mots-clés séparés par des virgules
        """
        try:
            # Nettoyer le texte
            text_clean = text.lower()
            
            # Supprimer les mots de remplissage
            filler_words = ["euh", "hmm", "ben", "alors", "voilà", "et puis", "donc"]
            for filler in filler_words:
                text_clean = text_clean.replace(filler, "")
            
            # Utiliser Groq pour extraire les mots-clés structurés
            prompt = f"""Extrait les mots-clés pertinents pour créer une histoire pour enfant.

TRANSCRIPTION: "{text}"

INSTRUCTIONS:
1. Identifie les personnages (dragon, princesse, etc.)
2. Identifie les lieux (château, forêt, etc.)
3. Identifie les objets/thèmes importants
4. Ignore les mots de remplissage

Réponds UNIQUEMENT en JSON:
{{
  "keywords": "mot1, mot2, mot3"
}}
"""
            
            response = self.client.chat.completions.create(
                model=GroqConfig.MODELS["fast"],  # Utiliser le modèle rapide
                messages=[
                    {"role": "system", "content": "Tu es un expert en extraction de mots-clés pour histoires d'enfants."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("keywords", text_clean)
            
        except Exception as e:
            print(f"⚠️  Extraction de mots-clés échouée, retour au texte nettoyé: {str(e)}")
            return text_clean
    
    def _evaluate_confidence(self, text: str) -> str:
        """
        Évaluer la confiance de la transcription
        
        Args:
            text: Texte transcrit
        
        Returns:
            "high", "medium" ou "low"
        """
        text_length = len(text.strip())
        
        if text_length == 0:
            return "error"
        elif text_length < 10:
            return "low"
        elif text_length < 50:
            return "medium"
        else:
            return "high"
    
    def transcribe_to_json(self, audio_file) -> str:
        """
        Transcrire et retourner directement en JSON string
        
        Args:
            audio_file: Fichier audio
        
        Returns:
            JSON string
        """
        result = self.transcribe_audio(audio_file)
        return json.dumps(result, ensure_ascii=False, indent=2)

# Instance globale
s2t_agent = S2TAgent()