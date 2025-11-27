from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.db.session import create_db_models
from app.api import auth

from app.web import routes as web_routes
from app.web import admin_routes  # Custom admin panel

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_models()
    yield

app = FastAPI(title="Ether Stories API", lifespan=lifespan)

#Mount Static Files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

#Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"]) # API
app.include_router(web_routes.router)  # <--- CRITICAL: THIS ADDS THE UI ROUTES
app.include_router(admin_routes.router)  # Custom admin panel at /admin