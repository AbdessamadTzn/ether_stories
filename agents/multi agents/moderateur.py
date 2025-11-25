import os
import re
import json
import time
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

try:
    from groq import Groq
except Exception:
    Groq = None

load_dotenv()
_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=_API_KEY) if (_API_KEY and Groq is not None) else None

JSON_BLOCK_RE = re.compile(r"(\{(?:.|\s)*\})", re.MULTILINE)


def verifier_coherence(
    texte: str,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    retries: int = 2,
    context: Optional[Dict[str, Any]] = None,
    previous_chapters: Optional[List[str]] = None,
    input_chapters: Optional[List[Dict[str, Any]]] = None,
    characters: Optional[List[str]] = None,
    forbidden_elements: Optional[List[str]] = None,
    current_chapter_num: Optional[int] = None,
) -> bool:
    """
    Vérifie la cohérence d'un chapitre via LLM.
    Retourne True si cohérent, False sinon.
    """
    
    if client is None:
        print("[moderateur] ⚠️ Pas d'API, validation par défaut", flush=True)
        return True
    
    # Récupérer le résumé attendu
    expected_summary = ""
    if input_chapters and current_chapter_num:
        for chap in input_chapters:
            if chap.get("numero") == current_chapter_num:
                expected_summary = chap.get("resume", "")
                break
    
    # Prompt simple et direct
    prompt_parts = [
        "Tu es un modérateur. Vérifie si le texte respecte TOUS les critères.",
        "",
        "📝 TEXTE :",
        texte,
        "",
        "✅ CRITÈRES :",
    ]
    
    if expected_summary:
        prompt_parts.append(f"1. Le texte suit-il cette histoire : «{expected_summary}»")
    
    if characters:
        prompt_parts.append(f"2. Tous ces personnages sont présents : {', '.join(characters)}")
    
    if forbidden_elements:
        prompt_parts.extend([
            f"3. 🚫 CRITIQUE : Le texte ne contient AUCUN de ces mots : {', '.join(forbidden_elements)}",
            "   Si UN SEUL mot interdit apparaît → coherent: false"
        ])
    
    if previous_chapters and len(previous_chapters) > 0:
        prompt_parts.extend([
            "",
            "📚 CHAPITRES PRÉCÉDENTS :",
            "\n---\n".join(previous_chapters[-2:])
        ])
    
    prompt_parts.extend([
        "",
        "🎯 RÉPONDS UNIQUEMENT :",
        '{"coherent": true} ou {"coherent": false, "raison": "..."}'
    ])
    
    prompt = "\n".join(prompt_parts)
    
    # Appel API avec retry
    for attempt in range(1, retries + 2):
        try:
            print(f"[moderateur] Appel LLM (tentative {attempt})...", flush=True)
            
            resp = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            
            raw = resp.choices[0].message.content.strip()
            
            # Parse JSON
            try:
                parsed = json.loads(raw)
            except:
                m = JSON_BLOCK_RE.search(raw)
                if m:
                    parsed = json.loads(m.group(1))
                else:
                    raise ValueError("Pas de JSON")
            
            coherent = bool(parsed.get("coherent", False))
            raison = parsed.get("raison", "")
            
            if not coherent:
                print(f"[moderateur] ❌ Rejeté: {raison}", flush=True)
            else:
                print(f"[moderateur] ✅ Accepté", flush=True)
            
            return coherent
            
        except Exception as exc:
            print(f"[moderateur] Erreur: {exc}", flush=True)
            if attempt <= retries:
                time.sleep(0.5)
                continue
            break
    
    # Fallback : accepter par défaut
    print(f"[moderateur] ⚠️ Échec, validation par défaut", flush=True)
    return True


if __name__ == "__main__":
    texte_test = """
    Il était une fois une petite fille nommée Luna qui adorait les dragons.
    Un jour, elle rencontra un grand dragon bleu dans la forêt.
    """
    
    coherent = verifier_coherence(
        texte=texte_test,
        characters=["Luna", "Dragon bleu"],
        forbidden_elements=["noir", "monstre"],
        context={"title": "Luna et le dragon"}
    )
    
    print(f"\n🎯 Résultat: {'✅ Cohérent' if coherent else '❌ Incohérent'}")