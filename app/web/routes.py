from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.core.graph.workflow import story_graph
from typing import Optional
import uuid
import asyncio

# Setup Templates
# This points to the 'app/templates' folder
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

# In-memory store for demo purposes (replace with DB in prod)
story_jobs = {}

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

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

@router.get("/create")
async def create_story_page(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@router.post("/api/story/generate")
async def generate_story_api(
    background_tasks: BackgroundTasks,
    age: int,
    topic: str,
    moral: Optional[str] = "Amitié",
    duration: Optional[int] = 5
):
    job_id = str(uuid.uuid4())
    
    initial_state = {
        "user_input": {
            "age": age,
            "keywords": topic,
            "moral": moral,
            "duree_minutes": duration
        },
        "generated_chapters": [],
        "is_complete": False
    }
    
    story_jobs[job_id] = {"status": "processing", "state": initial_state}
    
    background_tasks.add_task(run_story_generation, job_id, initial_state)
    
    return {"job_id": job_id, "status": "started"}

async def run_story_generation(job_id: str, initial_state: dict):
    try:
        final_state = await story_graph.ainvoke(initial_state)
        story_jobs[job_id]["status"] = "completed"
        story_jobs[job_id]["result"] = final_state
    except Exception as e:
        story_jobs[job_id]["status"] = "failed"
        story_jobs[job_id]["error"] = str(e)
        print(f"Job {job_id} failed: {e}")

@router.get("/api/story/status/{job_id}")
async def get_story_status(job_id: str):
    job = story_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return partial progress if available
    return {
        "status": job["status"],
        "chapters_count": len(job.get("result", {}).get("generated_chapters", [])) if job.get("result") else 0
    }

@router.get("/story/{job_id}")
async def view_story(request: Request, job_id: str):
    job = story_jobs.get(job_id)
    if not job or job["status"] != "completed":
        return templates.TemplateResponse("error.html", {"request": request, "message": "Story not ready or found"})
    
    story_data = job["result"]
    return templates.TemplateResponse("story.html", {"request": request, "story": story_data})
