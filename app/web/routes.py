from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Cookie, Depends, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.core.graph.workflow import story_graph
from typing import Optional
from jose import jwt, JWTError
from app.core.config import settings
from app.db.session import get_session
from app.db.models import User, Story, Chapter, StoryStatus, ChapterStatus
from app.agents.translator.translator import traduire_chapitre, get_language_name, SUPPORTED_LANGUAGES
from sqlmodel import Session, select
import uuid
import asyncio
import json
import os
import tempfile

# Setup Templates
# This points to the 'app/templates' folder
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

# In-memory store for demo purposes (replace with DB in prod)
story_jobs = {}

# Authentication dependency
async def get_current_user_from_cookie(request: Request, session: Session = Depends(get_session)):
    """
    Check if user is authenticated by validating JWT token from cookie.
    Returns User object if authenticated, raises HTTPException otherwise.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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
    # Redirect to my-stories page
    return RedirectResponse(url="/my-stories", status_code=302)

@router.get("/my-stories")
async def my_stories_page(
    request: Request,
    session: Session = Depends(get_session)
):
    # Check authentication
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return RedirectResponse(url="/login", status_code=302)
        
        # Get user
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        
        # Get user's stories
        stories = session.exec(
            select(Story).where(Story.user_id == user.id).order_by(Story.created_at.desc())
        ).all()
        
        return templates.TemplateResponse("my_stories.html", {
            "request": request,
            "stories": stories,
            "user_email": email
        })
        
    except JWTError:
        return RedirectResponse(url="/login", status_code=302)

@router.get("/create")
async def create_story_page(request: Request):
    # Check if user has a valid token
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return RedirectResponse(url="/login", status_code=302)
    except JWTError:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("create.html", {"request": request, "user_email": email})

# Directory for temporary audio uploads
AUDIO_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "audio" / "uploads"
AUDIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/api/audio/upload")
async def upload_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_cookie)
):
    """
    Upload audio file for speech-to-text transcription.
    Returns the file path for use in story generation.
    """
    # Validate file type
    allowed_types = ["audio/webm", "audio/wav", "audio/mp3", "audio/mpeg", "audio/ogg", "audio/mp4", "audio/x-m4a"]
    if audio.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Type de fichier non supporté: {audio.content_type}")
    
    # Generate unique filename
    file_ext = audio.filename.split(".")[-1] if "." in audio.filename else "webm"
    unique_filename = f"voice_{current_user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = AUDIO_UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        content = await audio.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return {"audio_path": str(file_path), "filename": unique_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'upload: {str(e)}")

@router.post("/api/story/generate")
async def generate_story_api(
    background_tasks: BackgroundTasks,
    age: int = 6,
    topic: Optional[str] = None,
    moral: Optional[str] = "Amitié",
    duration: Optional[int] = 5,
    audio_path: Optional[str] = None,
    current_user: User = Depends(get_current_user_from_cookie)
):
    """
    Generate a story. Can use either text input (topic) or voice input (audio_path).
    """
    # Validate: must have either topic OR audio_path
    if not topic and not audio_path:
        raise HTTPException(status_code=400, detail="Veuillez fournir un sujet ou un enregistrement vocal.")
    
    job_id = str(uuid.uuid4())
    
    initial_state = {
        "user_input": {
            "age": age,
            "keywords": topic or "",
            "moral": moral,
            "duree_minutes": duration,
            "audio_file": audio_path  # Will be transcribed in input_processing_node
        },
        "generated_chapters": [],
        "is_complete": False
    }
    
    story_jobs[job_id] = {"status": "processing", "state": initial_state, "user_id": current_user.id}
    
    background_tasks.add_task(run_story_generation, job_id, initial_state, current_user.id)
    
    return {"job_id": job_id, "status": "started"}

async def run_story_generation(job_id: str, initial_state: dict, user_id: int):
    try:
        final_state = await story_graph.ainvoke(initial_state)
        
        # Check for errors in final state
        if final_state.get("error"):
            story_jobs[job_id]["status"] = "failed"
            story_jobs[job_id]["error"] = final_state["error"]
            print(f"Job {job_id} failed: {final_state['error']}")
            return
        
        # Save to database
        from app.db.session import engine
        with Session(engine) as session:
            # Create Story record
            db_story = Story(
                user_id=user_id,
                title=final_state["plan"]["plan"]["titre"],
                plan_data=final_state["plan"],
                status=StoryStatus.COMPLETED
            )
            session.add(db_story)
            session.commit()
            session.refresh(db_story)
            
            # Create Chapter records
            for chapter_data in final_state["generated_chapters"]:
                db_chapter = Chapter(
                    story_id=db_story.id,
                    chapter_number=chapter_data["numero"],
                    title=chapter_data["titre"],
                    summary_prompt=chapter_data["resume"],
                    text_content=chapter_data.get("contenu"),
                    image_url=chapter_data.get("image_path"),
                    audio_url=chapter_data.get("audio_path"),
                    status=ChapterStatus.COMPLETED
                )
                session.add(db_chapter)
            
            session.commit()
            
            # Update job status with story_id
            story_jobs[job_id]["status"] = "completed"
            story_jobs[job_id]["result"] = final_state
            story_jobs[job_id]["story_id"] = db_story.id
            
            print(f"Job {job_id} completed and saved to DB (story_id: {db_story.id})")
            
    except Exception as e:
        story_jobs[job_id]["status"] = "failed"
        story_jobs[job_id]["error"] = str(e)
        print(f"Job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()

@router.get("/api/story/status/{job_id}")
async def get_story_status(job_id: str):
    job = story_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return partial progress if available
    response = {
        "status": job["status"],
        "chapters_count": len(job.get("result", {}).get("generated_chapters", [])) if job.get("result") else 0,
        "story_id": job.get("story_id")
    }
    
    # Include user-friendly error message if job failed
    if job["status"] == "failed" and job.get("error"):
        response["error_message"] = job.get("error")
    
    return response

@router.get("/story/{job_id}")
async def view_story(
    request: Request,
    job_id: str,
    lang: Optional[str] = None,
    session: Session = Depends(get_session)
):
    job = story_jobs.get(job_id)
    
    # If job exists and has story_id, load from database
    if job and job.get("story_id"):
        story_id = job["story_id"]
        story = session.get(Story, story_id)
        if story:
            chapters = session.exec(
                select(Chapter).where(Chapter.story_id == story_id).order_by(Chapter.chapter_number)
            ).all()
            
            # Get available translations
            available_translations = []
            if chapters and chapters[0].translations:
                available_translations = list(chapters[0].translations.keys())
            
            # Format for template (match existing structure)
            story_data = {
                "plan": story.plan_data,
                "generated_chapters": [
                    {
                        "id": ch.id,  # Chapter ID for audio generation
                        "numero": ch.chapter_number,
                        "titre": (
                            ch.translations[lang]["translated_title"] 
                            if (lang and ch.translations and lang in ch.translations and isinstance(ch.translations[lang], dict)) 
                            else ch.title
                        ),
                        "resume": ch.summary_prompt,
                        "contenu": (
                            ch.translations[lang]["translated_content"] 
                            if (lang and ch.translations and lang in ch.translations and isinstance(ch.translations[lang], dict)) 
                            else (ch.translations[lang] if (lang and ch.translations and lang in ch.translations and isinstance(ch.translations[lang], str)) else ch.text_content)
                        ),
                        "image_path": ch.image_url,
                        "audio_path": ch.audio_url
                    }
                    for ch in chapters
                ]
            }
            return templates.TemplateResponse("story.html", {
                "request": request,
                "story": story_data,
                "current_lang": lang,
                "available_translations": available_translations,
                "story_id": story_id
            })
    
    # Fallback to in-memory job data
    if not job or job["status"] != "completed":
        return templates.TemplateResponse("error.html", {"request": request, "message": "Story not ready or found"})
    
    story_data = job["result"]
    return templates.TemplateResponse("story.html", {"request": request, "story": story_data})

@router.get("/story/view/{story_id}")
async def view_story_by_id(
    request: Request,
    story_id: int,
    lang: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """View a story directly from database by its ID"""
    story = session.get(Story, story_id)
    
    if not story:
        return templates.TemplateResponse("error.html", {"request": request, "message": "Story not found"})
    
    # Optional: Check if user owns this story
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            user = session.exec(select(User).where(User.email == email)).first()
            # You could add a check here: if story.user_id != user.id: raise 403
        except JWTError:
            pass
    
    chapters = session.exec(
        select(Chapter).where(Chapter.story_id == story_id).order_by(Chapter.chapter_number)
    ).all()
    
    # Get available translations
    available_translations = []
    if chapters and chapters[0].translations:
        available_translations = list(chapters[0].translations.keys())
    
    # Format for template
    story_data = {
        "plan": story.plan_data,
        "generated_chapters": [
            {
                "id": ch.id,  # Chapter ID for audio generation
                "numero": ch.chapter_number,
                "titre": (
                    ch.translations[lang]["translated_title"] 
                    if (lang and ch.translations and lang in ch.translations and isinstance(ch.translations[lang], dict)) 
                    else ch.title
                ),
                "resume": ch.summary_prompt,
                "contenu": (
                    ch.translations[lang]["translated_content"] 
                    if (lang and ch.translations and lang in ch.translations and isinstance(ch.translations[lang], dict)) 
                    else (ch.translations[lang] if (lang and ch.translations and lang in ch.translations and isinstance(ch.translations[lang], str)) else ch.text_content)
                ),
                "image_path": ch.image_url,
                "audio_path": ch.audio_url
            }
            for ch in chapters
        ]
    }
    
    return templates.TemplateResponse("story.html", {
        "request": request,
        "story": story_data,
        "current_lang": lang,
        "available_translations": available_translations,
        "story_id": story_id
    })

# Translation endpoints
@router.post("/api/story/{story_id}/translate")
async def translate_story(
    story_id: int,
    lang: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_from_cookie),
    session: Session = Depends(get_session)
):
    """Translate a story to target language"""
    
    # Validate language
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")
    
    # Get story and verify ownership
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if translation already exists
    chapters = session.exec(
        select(Chapter).where(Chapter.story_id == story_id).order_by(Chapter.chapter_number)
    ).all()
    
    if chapters and chapters[0].translations and lang in chapters[0].translations:
        return {"status": "already_translated", "language": lang}
    
    # Start translation in background
    background_tasks.add_task(translate_story_task, story_id, lang)
    
    return {"status": "translating", "language": lang, "story_id": story_id}

async def translate_story_task(story_id: int, lang: str):
    """Background task to translate all chapters"""
    try:
        from app.db.session import engine
        from sqlalchemy.orm.attributes import flag_modified
        
        with Session(engine) as session:
            chapters = session.exec(
                select(Chapter).where(Chapter.story_id == story_id).order_by(Chapter.chapter_number)
            ).all()
            
            language_name = get_language_name(lang)
            
            for chapter in chapters:
                try:
                    # Translate chapter
                    translation = traduire_chapitre(
                        chapter_number=chapter.chapter_number,
                        title=chapter.title,
                        content=chapter.text_content or "",
                        langue_cible=language_name
                    )
                    
                    # Update translations field - create new dict to trigger change detection
                    if not chapter.translations:
                        chapter.translations = {}
                    
                    # Create new dict and assign to trigger SQLAlchemy change detection
                    new_translations = dict(chapter.translations)
                    new_translations[lang] = translation
                    chapter.translations = new_translations
                    
                    # Flag as modified for SQLAlchemy JSON column
                    flag_modified(chapter, "translations")
                    
                    session.add(chapter)
                    print(f"Translated chapter {chapter.chapter_number} to {language_name}")
                    
                except Exception as e:
                    print(f"Error translating chapter {chapter.chapter_number}: {e}")
                    continue
            
            session.commit()
            print(f"Story {story_id} fully translated to {language_name}")
            
    except Exception as e:
        print(f"Translation task failed for story {story_id}: {e}")
        import traceback
        traceback.print_exc()

@router.get("/api/story/{story_id}/translations")
async def get_story_translations(
    story_id: int,
    session: Session = Depends(get_session)
):
    """Get available translations for a story"""
    chapters = session.exec(
        select(Chapter).where(Chapter.story_id == story_id).limit(1)
    ).first()
    
    if not chapters:
        return {"translations": []}
    
    available_langs = list(chapters.translations.keys()) if chapters.translations else []
    
    return {
        "translations": [
            {"code": lang, "name": get_language_name(lang)}
            for lang in available_langs
        ],
        "supported_languages": [
            {"code": code, "name": name}
            for code, name in SUPPORTED_LANGUAGES.items()
        ]
    }

# Audio generation endpoint
@router.post("/api/chapter/{chapter_id}/audio/{lang}")
async def generate_chapter_audio(
    chapter_id: int,
    lang: str,
    current_user: User = Depends(get_current_user_from_cookie),
    session: Session = Depends(get_session)
):
    """
    Generate audio for a chapter in a specific language.
    On-demand generation - creates audio when user clicks "Listen".
    """
    from app.agents.speech.text_to_speech import generate_audio_for_translation
    
    # Get chapter
    chapter = session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Verify ownership through story
    story = session.get(Story, chapter.story_id)
    if not story or story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Handle French (original) audio
    if lang == "fr":
        if chapter.audio_url:
            return {"audio_url": chapter.audio_url, "cached": True}
        
        # Generate French audio from original content
        from app.agents.speech.text_to_speech import generate_audio
        audio_url = generate_audio(chapter.text_content, chapter.chapter_number, "fr")
        
        if audio_url:
            chapter.audio_url = audio_url
            session.add(chapter)
            session.commit()
            return {"audio_url": audio_url, "cached": False}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
    
    # Handle translated audio (en, zh)
    if lang not in ["en", "zh"]:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")
    
    # Check if audio already exists
    audio_translations = chapter.audio_translations or {}
    if lang in audio_translations and audio_translations[lang]:
        return {"audio_url": audio_translations[lang], "cached": True}
    
    # Check if translation exists
    translations = chapter.translations or {}
    if lang not in translations:
        raise HTTPException(status_code=400, detail=f"No translation available for {lang}. Translate first.")
    
    # Get translated text content
    translation_data = translations[lang]
    if isinstance(translation_data, dict):
        translated_text = translation_data.get("translated_content", "")
    else:
        translated_text = translation_data  # Old format: string only
    
    if not translated_text:
        raise HTTPException(status_code=400, detail="No translated content available")
    
    # Generate audio for translated content
    audio_url = generate_audio_for_translation(translated_text, chapter_id, lang)
    
    if audio_url:
        # Save audio URL
        audio_translations[lang] = audio_url
        chapter.audio_translations = audio_translations
        flag_modified(chapter, "audio_translations")
        session.add(chapter)
        session.commit()
        return {"audio_url": audio_url, "cached": False}
    else:
        raise HTTPException(status_code=500, detail="Failed to generate audio")

@router.get("/api/chapter/{chapter_id}/audio-status")
async def get_chapter_audio_status(
    chapter_id: int,
    session: Session = Depends(get_session)
):
    """Get available audio for a chapter in all languages"""
    chapter = session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    audio_status = {
        "fr": chapter.audio_url or None,
        "en": (chapter.audio_translations or {}).get("en"),
        "zh": (chapter.audio_translations or {}).get("zh"),
    }
    
    return {"audio": audio_status}
