import json
import time
import sys
from pathlib import Path

from app.agents.narrative_agent import dessinateur, ecrivain,moderateur



ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


OUTPUT_DIR = Path(__file__).resolve().parent / "chapitres"
OUTPUT_FILE = OUTPUT_DIR / "output.json"

def _ensure_output_file():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.write_text(
            json.dumps({"chapitres": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

def _load_output() -> dict:
    _ensure_output_file()
    raw = OUTPUT_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return {"chapitres": []}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"chapitres": []}

def _save_output(data: dict) -> None:
    _ensure_output_file()
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def _load_input() -> dict:
    input_path = ROOT_DIR / "input.json"
    return json.loads(input_path.read_text(encoding="utf-8"))

def _map_input_to_context(data: dict) -> Context:
    plan = data.get("plan", {})
    return Context(
        title=plan.get("titre", "Histoire"),
        story_type=plan.get("type_histoire", "conte"),
        target_age=int(plan.get("age_cible", 0)),
        main_character=plan.get("personnage_principal", ""),
        characters=data.get("personnages", []),
        moral=data.get("morale", {}).get("integration", ""),
        constraints=data.get("elements_cles", {}).get("contraintes", []),
    )

def _map_chapter_input(raw: dict) -> ChapterPrompt:
    return ChapterPrompt(
        chapter_number=int(raw.get("numero", 0)),
        title=raw.get("titre", f"Chapitre {raw.get('numero', '')}"),
        summary=raw.get("resume", ""),
        duration_minutes=int(raw.get("duree_minutes", 0)),
    )

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
                f"Personnages: {', '.join([c.nom for c in context.characters])}",
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
            story_text = ecrivain.generer_chapitre(prompt, max_tokens=1024, retries=2)
            
            if not story_text:
                raise RuntimeError("Texte vide")
            
            # 2️⃣ Vérification locale rapide
            story_lower = story_text.lower()
            violations = [m for m in peurs if m.lower() in story_lower]
            
            if violations:
                print(f"[orchestrateur] ❌ Violations locales: {violations}", flush=True)
                if tentative < max_retry:
                    continue
            
            # 3️⃣ Modérateur LLM (retourne bool)
            character_names = [
                c.nom if hasattr(c, 'nom') else c.get('nom', '') 
                for c in context.characters
            ]
            
            coherent = moderateur.verifier_coherence(
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
            
            # 5️⃣ Image (seulement si OK)
            image_path = None
            if coherent:
                img_prompt = f"{chapter.title} — {chapter.summary}"
                img_file = OUTPUT_DIR / f"chapter_{chapter.chapter_number}.png"
                try:
                    dessinateur.generer_image(img_prompt, img_file)
                    image_path = str(img_file)
                    print(f"[orchestrateur] ✅ Image: {image_path}", flush=True)
                except Exception as e:
                    print(f"[orchestrateur] ⚠️ Image échec: {e}", flush=True)
            
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

def main():
    data = _load_input()
    context = _map_input_to_context(data)
    chapters_raw = data.get("chapitres", [])

    output_data = _load_output()
    output_data.setdefault("chapitres", [])

    # 1️⃣ Manager crée le plan
    plan = manager_agent.create_story_plan(...)
    graph.publish("orchestrateur", "plan", plan)

    # 2️⃣ Boucle sur les chapitres
    for chap in plan["chapitres"]:
        # demande au writer
        graph.publish("orchestrateur", "write_request", chap)

        # attend le feedback du moderateur (via subscription)
        # si incohérent → réitérer, sinon → passer au dessinateur
        for raw in chapters_raw:
            chap_num = int(raw.get("numero", 0))
            if any(c["chapter_number"] == chap_num for c in output_data["chapitres"]):
                print(f"Chapitre {chap_num} déjà fait, skip", flush=True)
                continue

            chapter_prompt = _map_chapter_input(raw)
            print(f"\n=== Chapitre {chapter_prompt.chapter_number}: {chapter_prompt.title} ===", flush=True)

            previous_chapters = [c.get("story_text", "") for c in output_data.get("chapitres", [])]
            input_chapters = data.get("chapitres", [])

            result, meta = generer_chapitre(
                context,
                chapter_prompt,
                previous_chapters=previous_chapters,
                input_chapters=input_chapters,
                max_retry=3,
            )

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

            print(f"[output] Chapitre {result.chapter_number} → {OUTPUT_FILE}", flush=True)

    print("\n✅ Terminé !", flush=True)


if __name__ == "__main__":
    main()