from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional

class Character(BaseModel):
    nom: str = Field(..., alias="nom")
    role: Literal["principal", "secondaire"]
    description: str

    model_config = ConfigDict(populate_by_name=True)

class Context(BaseModel):
    title: str
    story_type: Literal["conte", "fable", "mythe"]
    target_age: int
    main_character: str
    characters: List[Character]
    moral: str
    constraints: List[str]          # ex. ["pas de noir", "pas de monstres"]

class ChapterPrompt(BaseModel):
    chapter_number: int = Field(..., ge=1)
    title: str
    summary: str
    duration_minutes: int

class ChapterResult(BaseModel):
    chapter_number: int
    story_text: str
    illustration_path: Optional[str] = None
    status: Optional[Literal["ok", "failed"]] = None
    error_message: Optional[str] = None