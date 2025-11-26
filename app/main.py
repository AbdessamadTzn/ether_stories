from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqladmin import Admin, ModelView

from app.db.session import engine, create_db_models
from app.db.models import User
from app.api import auth

# Lifecycle event to create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Checking Database Tables...")
    create_db_models()
    yield

app = FastAPI(title="Ether Stories Backend", lifespan=lifespan)

# 1. Include Auth Routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# 2. Setup Admin Panel
# Access this at http://localhost:8000/admin
admin = Admin(app, engine)

# Customize how the User table looks in the Admin Panel
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.role, User.is_active]
    column_searchable_list = [User.email, User.full_name]
    icon = "fa-solid fa-user"
    name = "User"
    name_plural = "Users"

admin.add_view(UserAdmin)

@app.get("/")
def root():
    return {
        "message": "Ether Stories API is running",
        "docs_url": "http://localhost:8000/docs",
        "admin_panel": "http://localhost:8000/admin"
    }