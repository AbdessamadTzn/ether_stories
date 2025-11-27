from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON

# --- USER MODELS ---
class UserRole(str, Enum):
    ADMIN = "admin"
    WRITER = "writer"
    USER = "user"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: Optional[str] = Field(default=None)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship: One User has many Stories
    stories: List["Story"] = Relationship(back_populates="user")

# Pydantic schemas for User Auth
class UserCreate(SQLModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserRead(SQLModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: UserRole

# --- STORY MODELS (New) ---

class StoryStatus(str, Enum):
    PLANNING = "planning"      # Manager is thinking
    READY = "ready"            # Plan approved by user
    GENERATING = "generating"  # Orchestrator is working
    COMPLETED = "completed"    # Done
    FAILED = "failed"

class Story(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default="Untitled Story")
    
    # Foreign Key to User
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="stories")
    
    # The massive JSON plan from the Manager Agent
    # Stores: target_age, moral, characters list, synopsis, etc.
    plan_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    status: StoryStatus = Field(default=StoryStatus.PLANNING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship: One Story has many Chapters
    chapters: List["Chapter"] = Relationship(back_populates="story")

class ChapterStatus(str, Enum):
    PENDING = "pending"
    WRITING = "writing"
    REVIEWING = "reviewing" # Moderator checking
    PAINTING = "painting"
    COMPLETED = "completed"
    REJECTED = "rejected"   # If moderator fails it repeatedly

class Chapter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign Key to Story
    story_id: int = Field(foreign_key="story.id")
    story: Story = Relationship(back_populates="chapters")
    
    chapter_number: int
    title: str
    summary_prompt: str # The specific instruction for this chapter
    
    # Content produced by Agents
    # We use sa_column=Column(JSON) if we want rich text, or just simple string if not.
    # For now, simple string is safer.
    text_content: Optional[str] = Field(default=None) 

    image_url: Optional[str] = None     # The illustration
    audio_url: Optional[str] = None     # The narrator output (French original)
    
    # Translations (e.g., {"en": {"titre": "...", "contenu": "..."}, "zh": {...}})
    translations: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    # Audio URLs for translations (e.g., {"en": "/static/audio/...", "zh": "/static/audio/..."})
    audio_translations: Dict[str, str] = Field(default={}, sa_column=Column(JSON))
    
    status: ChapterStatus = Field(default=ChapterStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)