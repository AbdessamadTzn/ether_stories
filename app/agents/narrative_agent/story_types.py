from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class Context:
    title: str
    story_type: str
    target_age: int
    main_character: str
    characters: List[Dict[str, Any]]
    moral: str
    constraints: List[str]

@dataclass
class ChapterPrompt:
    chapter_number: int
    title: str
    summary: str
    duration_minutes: int

@dataclass
class ChapterResult:
    chapter_number: int
    story_text: str
    illustration_path: str
    status: str
    error_message: Optional[str] = None