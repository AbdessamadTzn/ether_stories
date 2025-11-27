import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Ether Stories"
    VERSION: str = "1.0.0"
    
    # Database (Scaleway) x supbase for now (easy to modify)
    # Defaulting to sqlite for safety if env var is missing, but intended for Postgres
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ether_stories.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
    
    # AI Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    STABLE_DIFFUSION_API_KEY: str = os.getenv("STABLE_DIFFUSION_API_KEY")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY")

settings = Settings()