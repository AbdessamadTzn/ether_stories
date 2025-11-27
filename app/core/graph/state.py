from typing import TypedDict, List, Optional, Dict, Any

class Chapter(TypedDict):
    numero: int
    titre: str
    resume: str
    duree_minutes: int
    contenu: Optional[str]
    image_path: Optional[str]
    audio_path: Optional[str]
    traduction: Optional[Dict[str, str]] # {lang: content}

class StoryPlan(TypedDict):
    titre: str
    type_histoire: str
    duree_estimee: int
    age_cible: int
    personnage_principal: str
    chapitres: List[Dict[str, Any]] # Raw chapter plan
    morale: Dict[str, str]
    personnages: List[Dict[str, str]]
    elements_cles: Dict[str, List[str]]

class StoryState(TypedDict):
    # Inputs
    user_input: Dict[str, Any] # {age, topic, audio_file, etc.}
    
    # Processing
    transcription: Optional[str]
    keywords: Optional[List[str]]
    
    # Plan
    plan: Optional[StoryPlan]
    
    # Generation Loop
    current_chapter_index: int
    generated_chapters: List[Chapter]
    
    # Temporary holding for current chapter generation
    current_chapter_content: Optional[str]
    current_chapter_image: Optional[str]
    current_chapter_audio: Optional[str]
    
    # Errors
    error: Optional[str]
    retry_count: int
    
    # Status
    is_complete: bool
