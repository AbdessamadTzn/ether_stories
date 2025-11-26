import pytest
from app.core.graph.state import Chapter, StoryPlan, StoryState

def test_chapter_creation():
    """Test that a Chapter TypedDict can be instantiated with correct fields."""
    chapter: Chapter = {
        "numero": 1,
        "titre": "The Beginning",
        "resume": "Start of the journey",
        "duree_minutes": 5,
        "contenu": "Once upon a time...",
        "image_path": "/path/to/image.png",
        "audio_path": "/path/to/audio.mp3",
        "traduction": {"fr": "Il était une fois..."}
    }
    
    assert chapter["numero"] == 1
    assert chapter["titre"] == "The Beginning"
    assert chapter["contenu"] is not None
    assert chapter["traduction"]["fr"] == "Il était une fois..."

def test_chapter_optional_fields():
    """Test that optional fields in Chapter can be None."""
    chapter: Chapter = {
        "numero": 1,
        "titre": "The Beginning",
        "resume": "Start of the journey",
        "duree_minutes": 5,
        "contenu": None,
        "image_path": None,
        "audio_path": None,
        "traduction": None
    }
    
    assert chapter["contenu"] is None
    assert chapter["image_path"] is None

def test_story_plan_creation():
    """Test that a StoryPlan TypedDict can be instantiated."""
    plan: StoryPlan = {
        "titre": "My Story",
        "type_histoire": "Adventure",
        "duree_estimee": 10,
        "age_cible": 6,
        "personnage_principal": "Hero",
        "chapitres": [{"numero": 1, "titre": "Ch1"}],
        "morale": {"valeur_principale": "Courage"},
        "personnages": [{"nom": "Hero", "role": "Protagonist"}],
        "elements_cles": {"keywords_utilises": ["sword"]}
    }
    
    assert plan["titre"] == "My Story"
    assert len(plan["chapitres"]) == 1
    assert plan["morale"]["valeur_principale"] == "Courage"

def test_story_state_creation():
    """Test that a StoryState TypedDict can be instantiated."""
    state: StoryState = {
        "user_input": {"age": 6, "topic": "Dragons"},
        "transcription": None,
        "keywords": ["fire", "fly"],
        "plan": None,
        "current_chapter_index": 0,
        "generated_chapters": [],
        "current_chapter_content": None,
        "current_chapter_image": None,
        "current_chapter_audio": None,
        "error": None,
        "retry_count": 0,
        "is_complete": False
    }
    
    assert state["user_input"]["age"] == 6
    assert state["current_chapter_index"] == 0
    assert state["is_complete"] is False
    assert state["generated_chapters"] == []

def test_story_state_with_plan():
    """Test StoryState with a populated plan."""
    plan: StoryPlan = {
        "titre": "My Story",
        "type_histoire": "Adventure",
        "duree_estimee": 10,
        "age_cible": 6,
        "personnage_principal": "Hero",
        "chapitres": [],
        "morale": {},
        "personnages": [],
        "elements_cles": {}
    }
    
    state: StoryState = {
        "user_input": {},
        "transcription": None,
        "keywords": None,
        "plan": plan,
        "current_chapter_index": 0,
        "generated_chapters": [],
        "current_chapter_content": None,
        "current_chapter_image": None,
        "current_chapter_audio": None,
        "error": None,
        "retry_count": 0,
        "is_complete": False
    }
    
    assert state["plan"]["titre"] == "My Story"
