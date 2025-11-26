from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Setup Templates
# This points to the 'app/templates' folder
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.get("/signup")
async def signup_page(request: Request):
    # You would create a signup.html similar to login.html
    return templates.TemplateResponse("auth/signup.html", {"request": request}) 

@router.get("/dashboard")
async def dashboard(request: Request):
    # This page will need JS to check if localStorage has a token!
    return templates.TemplateResponse("base.html", {"request": request})