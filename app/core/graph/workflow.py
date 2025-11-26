from langgraph.graph import StateGraph, END
from app.core.graph.state import StoryState, Chapter
from app.agents.manager.manager import create_story_plan
from app.agents.narrative.writer import generate_chapter_content
from app.agents.narrative.moderator import verify_coherence
from app.agents.narrative.painter import generate_image
from app.agents.speech.t2s import generate_audio
from app.agents.speech.s2t import transcribe_audio

# --- NODES ---

def input_processing_node(state: StoryState) -> StoryState:
    """
    Processes input. If audio file is present, transcribes it.
    """
    user_input = state.get("user_input", {})
    audio_path = user_input.get("audio_file")
    
    if audio_path:
        result = transcribe_audio(audio_path)
        if "text" in result:
            return {"transcription": result["text"]}
        else:
            return {"error": f"Transcription failed: {result.get('error')}"}
    
    return {}

def manager_node(state: StoryState) -> StoryState:
    """
    Generates the story plan.
    """
    result = create_story_plan(state)
    if "error" in result:
        return {"error": result["error"]}
    
    return {
        "plan": result["plan"],
        "current_chapter_index": 0,
        "generated_chapters": [],
        "is_complete": False
    }

def writer_node(state: StoryState) -> StoryState:
    """
    Generates content for the current chapter.
    """
    plan = state["plan"]
    index = state["current_chapter_index"]
    chapter_info = plan["chapitres"][index]
    
    # Construct prompt
    prompt = f"""
    Titre de l'histoire: {plan['plan']['titre']}
    Chapitre {chapter_info['numero']}: {chapter_info['titre']}
    Résumé: {chapter_info['resume']}
    Personnages: {[p['nom'] for p in plan['personnages']]}
    Age cible: {plan['plan']['age_cible']}
    
    Ecris le contenu de ce chapitre (environ 300 mots).
    Style: Adapté aux enfants, engageant.
    """
    
    try:
        content = generate_chapter_content(prompt)
        return {"current_chapter_content": content, "error": None}
    except Exception as e:
        return {"error": str(e)}

def moderator_node(state: StoryState) -> StoryState:
    """
    Validates the generated chapter content.
    """
    content = state["current_chapter_content"]
    plan = state["plan"]
    
    context = {
        "age": plan["plan"]["age_cible"],
        "peurs_evitees": plan["elements_cles"]["peurs_evitees"]
    }
    
    result = verify_coherence(content, context)
    
    if result["coherent"]:
        return {"error": None}
    else:
        # If rejected, we could increment retry count or fail. 
        # For simplicity here, we'll just log error and maybe retry in a real loop.
        # Here we will just pass but mark error to trigger retry logic if we had it.
        return {"error": f"Moderation rejected: {result.get('reason')}"}

def painter_node(state: StoryState) -> StoryState:
    """
    Generates an image for the chapter.
    """
    content = state["current_chapter_content"]
    plan = state["plan"]
    index = state["current_chapter_index"]
    chapter_info = plan["chapitres"][index]
    
    prompt = f"Illustration pour enfant: {chapter_info['titre']}. {chapter_info['resume']}"
    
    image_path = generate_image(prompt, chapter_info['numero'])
    return {"current_chapter_image": image_path}

def narrator_node(state: StoryState) -> StoryState:
    """
    Generates audio for the chapter.
    """
    content = state["current_chapter_content"]
    index = state["current_chapter_index"]
    chapter_info = state["plan"]["chapitres"][index]
    
    audio_path = generate_audio(content, chapter_info['numero'])
    return {"current_chapter_audio": audio_path}

def chapter_finalize_node(state: StoryState) -> StoryState:
    """
    Finalizes the chapter and advances the index.
    """
    plan = state["plan"]
    index = state["current_chapter_index"]
    chapter_info = plan["chapitres"][index]
    
    new_chapter: Chapter = {
        "numero": chapter_info["numero"],
        "titre": chapter_info["titre"],
        "resume": chapter_info["resume"],
        "duree_minutes": chapter_info["duree_minutes"],
        "contenu": state["current_chapter_content"],
        "image_path": state.get("current_chapter_image"),
        "audio_path": state.get("current_chapter_audio"),
        "traduction": None
    }
    
    updated_chapters = state["generated_chapters"] + [new_chapter]
    next_index = index + 1
    is_complete = next_index >= len(plan["chapitres"])
    
    return {
        "generated_chapters": updated_chapters,
        "current_chapter_index": next_index,
        "is_complete": is_complete,
        "current_chapter_content": None, # Reset temp vars
        "current_chapter_image": None,
        "current_chapter_audio": None
    }

# --- EDGES ---

def check_error(state: StoryState):
    if state.get("error"):
        return END
    return "writer"

def check_input_output(state: StoryState):
    if state.get("error"):
        return END
    return "manager"

def check_completion(state: StoryState):
    if state.get("error"):
        return END
    if state["is_complete"]:
        return END
    return "writer"

def check_moderation(state: StoryState):
    if state.get("error"):
        # In a real system, we might route back to 'writer' to retry
        # For now, we stop on error to be safe
        return END 
    return "painter"

# --- GRAPH ---

workflow = StateGraph(StoryState)

workflow.add_node("input_processing", input_processing_node)
workflow.add_node("manager", manager_node)
workflow.add_node("writer", writer_node)
workflow.add_node("moderator", moderator_node)
workflow.add_node("painter", painter_node)
workflow.add_node("narrator", narrator_node)
workflow.add_node("finalize", chapter_finalize_node)

workflow.set_entry_point("input_processing")

workflow.add_conditional_edges(
    "input_processing",
    check_input_output,
    {
        "manager": "manager",
        END: END
    }
)

workflow.add_conditional_edges(
    "manager",
    check_error,
    {
        "writer": "writer",
        END: END
    }
)

workflow.add_edge("writer", "moderator")

workflow.add_conditional_edges(
    "moderator",
    check_moderation,
    {
        "painter": "painter",
        END: END
    }
)

workflow.add_edge("painter", "narrator")
workflow.add_edge("narrator", "finalize")

workflow.add_conditional_edges(
    "finalize",
    check_completion,
    {
        "writer": "writer",
        END: END
    }
)

story_graph = workflow.compile()
