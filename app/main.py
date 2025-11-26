from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin, ModelView
from pathlib import Path

from app.db.session import engine, create_db_models
# from app.db.models import User
from app.api import auth

from app.web import routes as web_routes 

from app.db.models import User, Story, Chapter

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

#Admin Panel
admin = Admin(app, engine)

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.role]
    icon = "fa-solid fa-user"
#Story View 
class StoryAdmin(ModelView, model=Story):
    column_list = [Story.id, Story.title, Story.status, Story.user_id]
    column_searchable_list = [Story.title]
    icon = "fa-solid fa-book"

#Chapter View
class ChapterAdmin(ModelView, model=Chapter):
    column_list = [Chapter.id, Chapter.story_id, Chapter.chapter_number, Chapter.title, Chapter.status]
    icon = "fa-solid fa-file-lines"

# Add views to admin
admin.add_view(UserAdmin)
admin.add_view(StoryAdmin)
admin.add_view(ChapterAdmin)