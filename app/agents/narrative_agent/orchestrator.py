"""
Orchestrateur - Génère les chapitres complets depuis plan.json
"""
import json
import time
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Imports locaux (sans relative imports)
import writer 
import moderator
import painter  # <-- ajouter l'import manquant
# Au lieu de définir les classes dans orchestrator.py
from story_types import Context, ChapterPrompt, ChapterResult

# Configuration des chemins
ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # ether_stories/
NARRATIVE_DIR = Path(__file__).resolve().parent  # narrative_agent/
OUTPUT_DIR = NARRATIVE_DIR / "chapitres"
OUTPUT_FILE = OUTPUT_DIR / "output.json"
PLAN_FILE = ROOT_DIR / "plan.json"  # plan.json à la racine

# Ajouter ROOT_DIR au path si nécessaire
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ==================== TYPES ====================
@dataclass
class Context:
    """Contexte global de l'histoire"""
    title: str
    story_type: str
    target_age: int
    main_character: str
    characters: list
    moral: str
    constraints: list


@dataclass
class ChapterPrompt:
    """Prompt pour un chapitre"""
    chapter_number: int
    title: str
    summary: str
    duration_minutes: int


@dataclass
class ChapterResult:
    """Résultat de génération d'un chapitre"""
    chapter_number: int
    story_text: str
    illustration_path: str
    status: str
    error_message: Optional[str] = None


# ==================== FONCTIONS UTILITAIRES ====================
def _ensure_output_file():
    """Crée le fichier output.json s'il n'existe pas"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.write_text(
            json.dumps({"chapitres": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _load_output() -> dict:
    """Charge le fichier output.json"""
    _ensure_output_file()
    raw = OUTPUT_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return {"chapitres": []}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"chapitres": []}


def _save_output(data: dict) -> None:
    """Sauvegarde dans output.json"""
    _ensure_output_file()
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_input() -> dict:
    """Charge le fichier plan.json"""
    if not PLAN_FILE.exists():
        raise FileNotFoundError(
            f"❌ Fichier plan.json introuvable !\n"
            f"Chemin attendu : {PLAN_FILE}\n"
            f"Veuillez d'abord générer un plan avec l'interface Streamlit."
        )
    
    return json.loads(PLAN_FILE.read_text(encoding="utf-8"))


def _map_input_to_context(data: dict) -> Context:
    """Convertit le plan.json en Context"""
    plan = data.get("plan", {})
    return Context(
        title=plan.get("titre", "Histoire"),
        story_type=plan.get("type_histoire", "conte"),
        target_age=int(plan.get("age_cible", 7)),
        main_character=plan.get("personnage_principal", ""),
        characters=data.get("personnages", []),
        moral=data.get("morale", {}).get("integration", ""),
        constraints=data.get("elements_cles", {}).get("peurs_evitees", []),
    )


def _map_chapter_input(raw: dict) -> ChapterPrompt:
    """Convertit un chapitre du plan en ChapterPrompt"""
    return ChapterPrompt(
        chapter_number=int(raw.get("numero", 0)),
        title=raw.get("titre", f"Chapitre {raw.get('numero', '')}"),
        summary=raw.get("resume", ""),
        duration_minutes=int(raw.get("duree_minutes", 2)),
    )


# ==================== GÉNÉRATION CHAPITRE ====================
def generer_chapitre(
    context: Context,
    chapter: ChapterPrompt,
    previous_chapters: list[str] | None = None,
    input_chapters: list[dict] | None = None,
    max_retry: int = 3,
) -> tuple[ChapterResult, dict]:
    """Génère un chapitre avec retry si rejeté par le modérateur."""
    
    input_data = _load_input()
    peurs = input_data.get("elements_cles", {}).get("peurs_evitees", [])
    
    for tentative in range(1, max_retry + 1):
        print(f"\n[orchestrateur] 📝 Tentative {tentative}/{max_retry}", flush=True)
        
        try:
            # 1️⃣ Prompt écrivain
            prompt_parts = [
                f"Titre: {context.title}",
                f"Chapitre {chapter.chapter_number}: {chapter.title}",
                f"Résumé à suivre EXACTEMENT: {chapter.summary}",
                f"Personnages: {', '.join([c.get('nom', '') for c in context.characters])}",
                f"Âge: {context.target_age} ans",
            ]
            
            if tentative > 1:
                prompt_parts.append(f"\n⚠️ TENTATIVE #{tentative} - Le texte précédent a été REJETÉ.")
                prompt_parts.append("RESPECTE TOUS LES CRITÈRES cette fois.")
            
            if peurs:
                prompt_parts.extend([
                    f"\n🚫 MOTS INTERDITS: {', '.join(peurs)}",
                    "N'utilise JAMAIS ces mots (même en métaphore).",
                    "Alternatives: 'bleu profond', 'violet doux', 'créature magique'",
                ])
            
            prompt_parts.extend([
                "\nÉcris 250-400 mots, joyeux et rassurant.",
                "Utilise les NOMS EXACTS des personnages.",
                "Suis le résumé fourni ci-dessus à la lettre.",
            ])
            
            prompt = "\n".join(prompt_parts)
            
            # Appel au writer
            story_text = writer.generer_chapitre(prompt, max_tokens=1024, retries=2)
            
            if not story_text:
                raise RuntimeError("Texte vide")
            
            # 2️⃣ Vérification locale rapide
            story_lower = story_text.lower()
            violations = [m for m in peurs if m.lower() in story_lower]
            
            if violations:
                print(f"[orchestrateur] ❌ Violations locales: {violations}", flush=True)
                if tentative < max_retry:
                    continue
            
            # 3️⃣ Modérateur LLM
            character_names = [c.get('nom', '') for c in context.characters]
            
            coherent = moderator.verifier_coherence(
                texte=story_text,
                context={"title": context.title, "main_character": context.main_character},
                previous_chapters=previous_chapters,
                input_chapters=input_chapters,
                characters=character_names,
                forbidden_elements=peurs,
                current_chapter_num=chapter.chapter_number,
            )
            
            # 4️⃣ Si rejeté → retry
            if not coherent and tentative < max_retry:
                print(f"[orchestrateur] ❌ Modérateur rejette, retry...", flush=True)
                time.sleep(1)
                continue
            
            # 5️⃣ Image (générer seulement si le chapitre est valide)
            image_path = None
            img_prompt = f"{chapter.title} — {chapter.summary}"
            img_file = OUTPUT_DIR / f"chapter_{chapter.chapter_number}.png"

            if coherent:
                try:
                    painter.generer_image(img_prompt, img_file)
                    if img_file.exists():
                        image_path = str(img_file)
                        print(f"[orchestrateur] ✅ Image sauvegardée: {image_path}", flush=True)
                    else:
                        print(f"[orchestrateur] ❌ Fichier image non créé", flush=True)
                except Exception as e:
                    print(f"[orchestrateur] ❌ Erreur génération image: {type(e).__name__}: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
            else:
                print("[orchestrateur] ℹ️ Chapitre non cohérent — image non générée", flush=True)
            
            # 6️⃣ Résultat
            result = ChapterResult(
                chapter_number=chapter.chapter_number,
                story_text=story_text,
                illustration_path=image_path or "",
                status="ok" if coherent else "failed",
                error_message=None if coherent else "Rejeté par modérateur",
            )
            meta = {
                "coherent": coherent,
                "image": image_path,
                "status": result.status,
                "tentatives": tentative,
            }
            return result, meta
            
        except Exception as exc:
            print(f"[orchestrateur] ❌ Erreur: {exc}", flush=True)
            if tentative >= max_retry:
                result = ChapterResult(
                    chapter_number=chapter.chapter_number,
                    story_text="",
                    illustration_path="",
                    status="failed",
                    error_message=str(exc),
                )
                meta = {"coherent": False, "image": None, "status": "failed", "tentatives": tentative}
                return result, meta
            time.sleep(1)
            continue
    
    # Fallback final
    result = ChapterResult(
        chapter_number=chapter.chapter_number,
        story_text="",
        illustration_path="",
        status="failed",
        error_message=f"Échec après {max_retry} tentatives",
    )
    meta = {"coherent": False, "image": None, "status": "failed", "tentatives": max_retry}
    return result, meta


# ==================== MAIN ====================
def main():
    """Point d'entrée principal"""
    print("\n" + "="*60)
    print("🎭 ORCHESTRATEUR - Génération des chapitres")
    print("="*60)
    
    # Charger le plan
    try:
        data = _load_input()
        print(f"✅ Plan chargé: {PLAN_FILE}")
    except FileNotFoundError as e:
        print(str(e))
        return
    
    context = _map_input_to_context(data)
    chapters_raw = data.get("chapitres", [])
    
    print(f"\n📚 Histoire: {context.title}")
    print(f"📖 {len(chapters_raw)} chapitres à générer")
    print(f"🎯 Âge cible: {context.target_age} ans")
    
    # Charger l'output existant
    output_data = _load_output()
    output_data.setdefault("chapitres", [])
    
    # Générer chaque chapitre
    for raw in chapters_raw:
        chap_num = int(raw.get("numero", 0))
        
        # Skip si déjà généré
        if any(c["chapter_number"] == chap_num for c in output_data["chapitres"]):
            print(f"\n⏭️  Chapitre {chap_num} déjà généré, skip", flush=True)
            continue
        
        chapter_prompt = _map_chapter_input(raw)
        print(f"\n{'='*60}")
        print(f"📖 Chapitre {chapter_prompt.chapter_number}: {chapter_prompt.title}")
        print(f"{'='*60}")
        
        previous_chapters = [c.get("story_text", "") for c in output_data.get("chapitres", [])]
        input_chapters = data.get("chapitres", [])
        
        result, meta = generer_chapitre(
            context,
            chapter_prompt,
            previous_chapters=previous_chapters,
            input_chapters=input_chapters,
            max_retry=3,
        )
        
        # Sauvegarder le résultat
        entry = {
            "chapter_number": result.chapter_number,
            "title": chapter_prompt.title,
            "summary": chapter_prompt.summary,
            "story_text": result.story_text,
            "image": meta["image"],
            "status": meta["status"],
            "coherent": meta["coherent"],
            "tentatives": meta.get("tentatives", 1),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        output_data["chapitres"].append(entry)
        _save_output(output_data)
        
        print(f"\n💾 Chapitre {result.chapter_number} sauvegardé dans {OUTPUT_FILE}")
    
    print("\n" + "="*60)
    print("✅ Génération terminée !")
    print(f"📁 Résultats: {OUTPUT_FILE}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()