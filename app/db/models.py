from typing import Optional
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field


# Define Roles
class UserRole(str, Enum):
    ADMIN = "admin"
    WRITER = "writer"
    USER = "user"

# Main User Table
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str = None
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Schema for SIGN UP
class UserCreate(SQLModel):
    full_name: str = None
    email: str 
    password: str

# Schema for Response
class UserRead(SQLModel):
    id: int
    email: str
    full_name: str = None
    role: UserRole
