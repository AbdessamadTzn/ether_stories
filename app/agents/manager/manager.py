"""
Agent Manager
Orchestre la création du plan d'histoire complet
Fichier adapté pour fonctionner sans GroqConfig : configuration locale et client Groq par agent.
"""
from typing import List, Optional, Dict, Any
import json
import os
import re
from groq import Groq
from dotenv import load_dotenv

# Prompts
try:
    from .manager_prompt import get_system_prompt, get_user_prompt
except Exception:
    try:
        from manager_prompt import get_system_prompt, get_user_prompt
    except Exception:
        # fallback prompts minimal pour éviter crash si manager_prompt.py est vide
        def get_system_prompt() -> str:
            return "Tu es un planificateur d'histoires pour enfants et tu dois renvoyer un JSON structuré."

        def get_user_prompt(
            age, interests, peurs, keywords, moral, type_histoire, duree_minutes, personnage, transcription=None, manager_decides=True
        ) -> str:
            return (
                f"Crée un plan pour une histoire d'enfant.\n"
                f"age: {age}\ninterests: {interests}\npeurs: {peurs}\nkeywords: {keywords}\n"
                f"moral: {moral}\ntype: {type_histoire}\nduree_minutes: {duree_minutes}\npersonnage: {personnage}\n\n"
                "Format: JSON avec clefs 'plan', 'chapitres', 'personnages', 'morale', 'elements_cles'."
            )

load_dotenv()

# Configuration locale (chaque agent garde ses propres defaults)
DEFAULT_MODEL = os.getenv("MANAGER_MODEL", "openai/gpt-oss-120b")
DEFAULT_TEMPERATURE = float(os.getenv("MANAGER_TEMPERATURE", "0.2"))
DEFAULT_MAX_TOKENS = int(os.getenv("MANAGER_MAX_TOKENS", "2048"))

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("GROQ_API_KEY is required in environment for ManagerAgent")

class ManagerAgent:
    """
    Agent Manager - Chef d'orchestre
    INPUT: dict décrivant préférences et contraintes
    OUTPUT: dict plan d'histoire (JSON dict)
    """
    def __init__(self):
        self.name = "Agent Manager"
        self.model = DEFAULT_MODEL
        self.params = {"temperature": DEFAULT_TEMPERATURE, "max_tokens": DEFAULT_MAX_TOKENS}
        self.client = Groq(api_key=API_KEY)
        print(f"✅ {self.name} initialisé | modèle: {self.model}")

    def _get_text_from_response(self, resp) -> str:
        """
        Robustly extract the textual content from various Groq/OpenAI-like client response shapes.
        """
        # Try attribute-style access
        if resp is None:
            return ""
        # object with output_text attribute
        text = getattr(resp, "output_text", None)
        if text:
            return text
        # dict-like exposes 'output_text' or 'output'
        if isinstance(resp, dict):
            if "output_text" in resp:
                return resp["output_text"]
            if "output" in resp and isinstance(resp["output"], list):
                # try to find content->text in nested structures
                for block in resp["output"]:
                    content = block.get("content") if isinstance(block, dict) else None
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                return item["text"]
        # compatibility with OpenAI style
        if isinstance(resp, dict) and "choices" in resp:
            try:
                choices = resp["choices"]
                if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                    # content can be a string or dict
                    c = choices[0]["message"]["content"]
                    if isinstance(c, str):
                        return c
                    if isinstance(c, dict):
                        # sometimes it's {"type":"output_text","text":"..."}
                        return c.get("text", "")
            except Exception:
                pass

        # Attribute style nested content
        out = getattr(resp, "output", None)
        if out:
            try:
                # out could be list-like with content->text
                if isinstance(out, list):
                    for block in out:
                        content = getattr(block, "content", None) or (block.get("content") if isinstance(block, dict) else None)
                        if content:
                            if isinstance(content, list):
                                for item in content:
                                    text = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                                    if text:
                                        return text
            except Exception:
                pass

        # Fallback to string representation
        try:
            return str(resp)
        except Exception:
            return ""

    def _llm_request(self, messages: list) -> str:
        """
        Try multiple Groq client call patterns and return raw textual output.
        """
        last_exc = None
        # Pattern 1: responses.create
        try:
            if hasattr(self.client, "responses") and hasattr(self.client.responses, "create"):
                resp = self.client.responses.create(messages=messages, model=self.model, **self.params)
                return self._get_text_from_response(resp)
        except Exception as e:
            last_exc = e

        # Pattern 2: chat.completions.create
        try:
            if hasattr(self.client, "chat") and hasattr(self.client.chat, "completions") and hasattr(self.client.chat.completions, "create"):
                resp = self.client.chat.completions.create(messages=messages, model=self.model, **self.params)
                # Extract content from ChatCompletion
                if hasattr(resp, 'choices') and len(resp.choices) > 0:
                    return resp.choices[0].message.content
                return self._get_text_from_response(resp)
        except Exception as e:
            last_exc = e

        # Pattern 3: completions.create
        try:
            if hasattr(self.client, "completions") and hasattr(self.client.completions, "create"):
                resp = self.client.completions.create(messages=messages, model=self.model, **self.params)
                return self._get_text_from_response(resp)
        except Exception as e:
            last_exc = e

        # Pattern 4: generic create / create_response (older/other clients)
        try:
            if hasattr(self.client, "create"):
                resp = self.client.create(messages=messages, model=self.model, **self.params)
                return self._get_text_from_response(resp)
        except Exception as e:
            last_exc = e

        # Nothing worked — raise the last exception for debugging
        raise AttributeError(
            "Could not call Groq LLM: client has no supported interface (checked responses/chat/completions/create)."
            f" Last exception: {last_exc}"
        )

    def _clean_json_string(self, text: str) -> str:
        """
        Nettoie le texte pour extraire uniquement le JSON valide.
        Supprime les balises markdown et autres préfixes/suffixes.
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Supprimer les balises markdown ```json ... ```
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        
        # Supprimer "json" au début s'il est seul sur une ligne
        text = re.sub(r'^json\s*\n', '', text, flags=re.MULTILINE)
        
        return text.strip()

    def _extract_json_object_from_text(self, text: str) -> str:
        """
        Extraire le 1er JSON object or JSON array présent dans la réponse.
        Retourne la string JSON trouvée ou lève ValueError si introuvable.
        """
        if not text or not isinstance(text, str):
            raise ValueError("Aucune réponse texte à analyser.")

        # D'abord nettoyer les balises markdown
        text = self._clean_json_string(text)

        # Cherche premier '{' ou '[' et tente d'équilibrer crochets
        for open_c, close_c in (('{', '}'), ('[', ']')):
            start_idx = text.find(open_c)
            if start_idx == -1:
                continue
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == open_c:
                    depth += 1
                elif text[i] == close_c:
                    depth -= 1
                    if depth == 0:
                        return text[start_idx:i + 1]

        # Fallback: regex greedy for JSON object
        m = re.search(r'(\{[\s\S]*\})', text)
        if m:
            return m.group(1)

        raise ValueError("Impossible de trouver un objet JSON dans la réponse.")

    def _safe_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """
        Tente de parser du JSON depuis raw_text.
        - Nettoie d'abord les balises markdown
        - Si json.loads échoue, tente d'extraire le JSON via _extract_json_object_from_text,
          puis réessaye json.loads.
        - Lève ValueError si rien de valide trouvé.
        """
        if not raw_text:
            raise ValueError("Réponse du modèle vide.")

        # 1/ Nettoyer les balises markdown
        cleaned_text = self._clean_json_string(raw_text)

        # 2/ Try direct parse on cleaned text
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass

        # 3/ Try to extract a JSON substring
        try:
            json_snippet = self._extract_json_object_from_text(cleaned_text)
            return json.loads(json_snippet)
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Impossible de parser le JSON renvoyé par le modèle: {e}\n--- raw ---\n{raw_text[:2000]}")

    def create_story_plan(
        self,
        age: int,
        interests: List[str],
        peurs: List[str],
        keywords: str,
        moral: str,
        type_histoire: str,
        duree_minutes: int,
        personnage: str,
        nom_enfant: Optional[str] = None,
        transcription_raw: Optional[str] = None,
        manager_decides: bool = True
    ) -> Dict[str, Any]:
        """
        Crée un plan d'histoire.
        Si transcription_raw est fournie, le Manager doit s'en servir comme source principale; keywords sont des hints.
        """
        system_prompt = get_system_prompt()
        user_prompt = get_user_prompt(
            age=age,
            interests=interests,
            peurs=peurs,
            keywords=keywords,
            moral=moral,
            type_histoire=type_histoire,
            duree_minutes=duree_minutes,
            personnage=personnage,
            transcription=transcription_raw,
            manager_decides=manager_decides
        )

        # Construct messages
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        
        raw_content = ""
        try:
            raw_content = self._llm_request(messages)
            print(f"\n📄 Réponse brute du modèle (150 premiers caractères):\n{raw_content[:150]}...")
            
            plan = self._safe_parse_json(raw_content)
            
            if not self._validate_plan(plan):
                raise ValueError("Plan généré invalide selon la validation interne.")
            
            # ✅ SAUVEGARDE AUTOMATIQUE DANS plan.json
            with open("plan.json", "w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)
            print(f"✅ Plan sauvegardé dans plan.json")
            
            return plan  # Retourner directement le plan, pas un dict avec 'success'

        except Exception as e:
            print(f"\n⚠️ Erreur première tentative: {e}")
            print(f"📄 Contenu brut (500 premiers caractères):\n{raw_content[:500] if raw_content else 'Aucun contenu'}")
            
            # try a second pass to reformat to pure JSON with explicit structure
            try:
                follow_up = [
                    {"role": "system", "content": """Tu es un formatteur JSON strict. Tu dois retourner UNIQUEMENT un JSON valide avec cette structure EXACTE:
{
  "plan": {"titre": "...", "type_histoire": "...", "duree_estimee": 10, "age_cible": 7, "personnage_principal": "..."},
  "chapitres": [{"numero": 1, "titre": "...", "resume": "...", "duree_minutes": 3}],
  "morale": {"valeur_principale": "...", "message": "...", "integration": "..."},
  "personnages": [{"nom": "...", "role": "...", "description": "..."}],
  "elements_cles": {"keywords_utilises": [], "interets_integres": [], "peurs_evitees": []}
}
SANS balises markdown, SANS texte avant ou après."""},
                    {"role": "user", "content": f"Voici une réponse mal formatée. Extrais et reformate UNIQUEMENT le JSON avec la structure exacte demandée:\n\n{raw_content if raw_content else str(e)}"}
                ]
                print("\n🔄 Deuxième tentative avec reformatage...")
                raw2 = self._llm_request(follow_up)
                print(f"📄 Réponse reformatée (150 premiers caractères):\n{raw2[:150]}...")
                
                plan = self._safe_parse_json(raw2)
                
                if not self._validate_plan(plan):
                    raise ValueError("Plan reformaté invalide selon la validation.")
                
                print("✅ Deuxième tentative réussie!")
                
                # ✅ SAUVEGARDE AUTOMATIQUE DANS plan.json
                with open("plan.json", "w", encoding="utf-8") as f:
                    json.dump(plan, f, ensure_ascii=False, indent=2)
                print(f"✅ Plan sauvegardé dans plan.json")
                
                return plan  # Retourner directement le plan
                
            except Exception as e2:
                print(f"\n❌ Erreur deuxième tentative: {e2}")
                raise ValueError(
                    f"Impossible de parser le JSON renvoyé par le modèle après 2 tentatives.\n"
                    f"Erreur 1: {str(e)}\n"
                    f"Erreur 2: {str(e2)}\n"
                    f"Contenu brut (1000 premiers caractères):\n{raw_content[:1000] if raw_content else 'Aucun contenu'}"
                )

    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Validation minimale sur la structure du plan.
        Lève ValueError si invalide.
        """
        if not isinstance(plan, dict):
            raise ValueError("Plan attendu en JSON/dict")

        required_keys = ["plan", "chapitres", "morale", "personnages", "elements_cles"]
        for k in required_keys:
            if k not in plan:
                raise ValueError(f"Plan incomplet: clé manquante '{k}'")

        if "titre" not in plan["plan"]:
            raise ValueError("Plan.plan.titre manquant")

        if not isinstance(plan["chapitres"], list) or len(plan["chapitres"]) == 0:
            raise ValueError("Plan.chapitres doit être une liste non vide")

        return True

    def create_plan_from_json(self, input_json: str) -> str:
        """
        Transforme un JSON d'entrée (string) en plan (string JSON).
        Utilisé pour tests rapides ou pour réutilisation de JSON externe.
        """
        try:
            data = json.loads(input_json)
            plan_dict = self.create_story_plan(
                age=data.get("age", 6),
                interests=data.get("interests", []),
                peurs=data.get("peurs", []),
                keywords=data.get("keywords", ""),
                moral=data.get("moral", ""),
                type_histoire=data.get("type_histoire", "aventure"),
                duree_minutes=data.get("duree_minutes", 10),
                personnage=data.get("personnage", ""),
                nom_enfant=data.get("nom_enfant"),
            )
            return json.dumps(plan_dict, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            raise ValueError("input_json must be a valid JSON string")
        except Exception as e:
            raise RuntimeError(f"create_plan_from_json error: {e}")

    def create_plan_from_audio(
        self,
        audio_file,
        age: int = 7,
        interests: list = None,
        peurs: list = None,
        moral: str = "courage et amitié",
        type_histoire: str = "aventure",
        duree_minutes: int = 10,
        personnage: str = "",
        nom_enfant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        🔗 NOUVELLE MÉTHODE DE CONNEXION
        Crée un plan d'histoire directement depuis un fichier audio
        """
        # Import du S2TAgent (lazy import pour éviter les dépendances circulaires)
        try:
            from ..speech_to_text.seepch_to_text import s2t_agent
        except (ImportError, ValueError):
            try:
                from agents.speech_to_text.seepch_to_text import s2t_agent
            except ImportError:
                try:
                    from speech_to_text import s2t_agent
                except ImportError:
                    raise ImportError(
                        "Impossible d'importer s2t_agent. "
                        "Vérifiez que seepch_to_text.py est accessible."
                    )
        
        print(f"\n🎤 Étape 1/2: Transcription de l'audio...")
        transcription_result = s2t_agent.transcribe_audio(audio_file)
        
        if not transcription_result["success"]:
            raise RuntimeError(f"Échec de la transcription: {transcription_result.get('error', 'Erreur inconnue')}")
        
        keywords = transcription_result["keywords"]
        print(f"✅ Mots-clés extraits: {keywords}")
        
        if not personnage and keywords:
            first_keyword = keywords.split(",")[0].strip()
            personnage = first_keyword
        
        print(f"\n📖 Étape 2/2: Création du plan d'histoire...")
        story_plan = self.create_story_plan(
            age=age,
            interests=interests or [],
            peurs=peurs or [],
            keywords=keywords,
            moral=moral,
            type_histoire=type_histoire,
            duree_minutes=duree_minutes,
            personnage=personnage,
            nom_enfant=nom_enfant
        )
        
        print(f"✅ Plan créé: {story_plan['plan']['titre']}")
        
        # Ajouter les infos de transcription au résultat
        story_plan["_metadata"] = {
            "transcription": transcription_result["transcription_raw"],
            "keywords_extracted": keywords,
            "confidence": transcription_result["confidence"]
        }
        
        return story_plan

# Instance globale exportée
manager_agent = ManagerAgent()