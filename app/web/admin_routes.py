"""
Admin Panel Routes
==================
Routes for admin dashboard, user management, and story management.
Only accessible by users with role='admin'.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path
from app.db.models import User, Story, Chapter, CarbonEmission, UserRole, StoryStatus
from app.db.session import get_session
from app.core.config import settings
from app.core.logger import get_logger
from sqlmodel import Session, select, func
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional

logger = get_logger("admin")

# Setup Templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================
# ADMIN AUTHENTICATION MIDDLEWARE
# ============================================================

async def get_admin_user(request: Request, session: Session = Depends(get_session)) -> User:
    """
    Check if user is authenticated AND is an admin.
    Returns User object if admin, raises HTTPException otherwise.
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
        
        # Check if user is admin
        if user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@router.get("")
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Main admin dashboard with overview stats."""
    
    # Calculate date ranges
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get total users
    total_users = session.exec(select(func.count(User.id))).one()
    new_users_week = session.exec(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    ).one()
    
    # Get total stories
    total_stories = session.exec(select(func.count(Story.id))).one()
    stories_today = session.exec(
        select(func.count(Story.id)).where(Story.created_at >= today_start)
    ).one()
    
    # Get total CO2
    total_co2_result = session.exec(
        select(func.sum(CarbonEmission.emissions_kg))
    ).one()
    total_co2_kg = total_co2_result or 0
    total_co2_grams = total_co2_kg * 1000
    
    # Get total operations
    total_operations = session.exec(select(func.count(CarbonEmission.id))).one()
    
    # Get top users by story count
    top_users_query = """
        SELECT u.id, u.email, COUNT(s.id) as story_count, 
               COALESCE(SUM(ce.emissions_kg), 0) * 1000 as co2_grams
        FROM "user" u
        LEFT JOIN story s ON u.id = s.user_id
        LEFT JOIN carbonemission ce ON u.id = ce.user_id
        GROUP BY u.id, u.email
        ORDER BY story_count DESC
        LIMIT 10
    """
    from sqlalchemy import text
    top_users_result = session.exec(text(top_users_query)).fetchall()
    top_users = [
        {"email": r[1], "story_count": r[2], "co2_grams": r[3] or 0}
        for r in top_users_result
    ]
    
    # Get recent stories
    recent_stories_stmt = (
        select(Story, User.email)
        .join(User)
        .order_by(Story.created_at.desc())
        .limit(10)
    )
    recent_stories_result = session.exec(recent_stories_stmt).fetchall()
    recent_stories = [
        {
            "title": s.title,
            "user_email": email,
            "status": s.status.value if hasattr(s.status, 'value') else s.status,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for s, email in recent_stories_result
    ]
    
    # Get CO2 by operation type
    co2_by_type_query = """
        SELECT operation_type, COUNT(*) as count, SUM(emissions_kg) * 1000 as emissions_grams
        FROM carbonemission
        GROUP BY operation_type
    """
    co2_by_type_result = session.exec(text(co2_by_type_query)).fetchall()
    co2_by_type = {
        r[0]: {"count": r[1], "emissions_grams": r[2] or 0}
        for r in co2_by_type_result
    }
    
    stats = {
        "total_users": total_users,
        "new_users_week": new_users_week,
        "total_stories": total_stories,
        "stories_today": stories_today,
        "total_co2_grams": total_co2_grams,
        "total_operations": total_operations,
        "top_users": top_users,
        "recent_stories": recent_stories,
        "co2_by_type": co2_by_type
    }
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
        "current_user": current_user
    })


# ============================================================
# USER MANAGEMENT
# ============================================================

@router.get("/users")
async def admin_users_page(
    request: Request,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """User management page."""
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    # Get all users with their stats
    users_query = """
        SELECT u.id, u.email, u.full_name, u.role, u.is_active, u.created_at,
               COUNT(DISTINCT s.id) as story_count,
               COALESCE(SUM(ce.emissions_kg), 0) * 1000 as co2_grams
        FROM "user" u
        LEFT JOIN story s ON u.id = s.user_id
        LEFT JOIN carbonemission ce ON u.id = ce.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """
    from sqlalchemy import text
    users_result = session.exec(text(users_query)).fetchall()
    
    users = [
        {
            "id": r[0],
            "email": r[1],
            "full_name": r[2],
            "role": r[3],
            "is_active": r[4],
            "created_at": r[5].strftime("%Y-%m-%d") if r[5] else "",
            "story_count": r[6],
            "co2_grams": r[7] or 0
        }
        for r in users_result
    ]
    
    # Stats
    total = len(users)
    active = sum(1 for u in users if u["is_active"])
    admins = sum(1 for u in users if u["role"] == "admin")
    new_this_week = session.exec(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    ).one()
    
    stats = {
        "total": total,
        "active": active,
        "admins": admins,
        "new_this_week": new_this_week
    }
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users,
        "stats": stats,
        "current_user": current_user
    })


@router.get("/api/user/{user_id}")
async def get_user_details(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get user details for modal."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's CO2
    co2_result = session.exec(
        select(func.sum(CarbonEmission.emissions_kg))
        .where(CarbonEmission.user_id == user_id)
    ).one()
    co2_kg = co2_result or 0
    
    # Get recent stories
    stories_stmt = (
        select(Story)
        .where(Story.user_id == user_id)
        .order_by(Story.created_at.desc())
        .limit(5)
    )
    stories = session.exec(stories_stmt).all()
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M"),
        "story_count": len(stories),
        "co2_grams": co2_kg * 1000,
        "recent_stories": [
            {"title": s.title, "created_at": s.created_at.strftime("%Y-%m-%d")}
            for s in stories
        ]
    }


@router.put("/api/user/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update user details."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = await request.json()
    
    # Update fields
    if "email" in data:
        user.email = data["email"]
    if "full_name" in data:
        user.full_name = data["full_name"]
    if "role" in data:
        user.role = UserRole(data["role"])
    if "is_active" in data:
        user.is_active = data["is_active"]
    
    session.add(user)
    session.commit()
    
    logger.info(f"Admin {current_user.email} updated user {user.email}")
    
    return {"status": "success"}


@router.delete("/api/user/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete user and all their data."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself or other admins
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot delete admin users")
    
    user_email = user.email
    
    # Delete user's carbon emissions
    session.exec(
        select(CarbonEmission).where(CarbonEmission.user_id == user_id)
    )
    from sqlalchemy import delete
    session.exec(delete(CarbonEmission).where(CarbonEmission.user_id == user_id))
    
    # Delete user's chapters (via stories)
    stories = session.exec(select(Story).where(Story.user_id == user_id)).all()
    for story in stories:
        session.exec(delete(Chapter).where(Chapter.story_id == story.id))
    
    # Delete user's stories
    session.exec(delete(Story).where(Story.user_id == user_id))
    
    # Delete user
    session.delete(user)
    session.commit()
    
    logger.info(f"Admin {current_user.email} deleted user {user_email}")
    
    return {"status": "success"}


# ============================================================
# STORY MANAGEMENT
# ============================================================

@router.get("/stories")
async def admin_stories_page(
    request: Request,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Story management page."""
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get all stories with user info
    stories_stmt = (
        select(Story, User.email)
        .join(User)
        .order_by(Story.created_at.desc())
    )
    stories_result = session.exec(stories_stmt).fetchall()
    
    stories = []
    for story, user_email in stories_result:
        # Get chapter count
        chapter_count = session.exec(
            select(func.count(Chapter.id)).where(Chapter.story_id == story.id)
        ).one()
        
        # Get duration from plan_data
        duration = 5  # default
        if story.plan_data and "plan" in story.plan_data:
            duration = story.plan_data.get("plan", {}).get("duree_estimee", 5)
        
        stories.append({
            "id": story.id,
            "title": story.title,
            "user_email": user_email,
            "chapter_count": chapter_count,
            "duration": duration,
            "status": story.status.value if hasattr(story.status, 'value') else story.status,
            "created_at": story.created_at.strftime("%Y-%m-%d %H:%M")
        })
    
    # Stats
    total = len(stories)
    completed = sum(1 for s in stories if s["status"] == "completed")
    failed = sum(1 for s in stories if s["status"] == "failed")
    today = session.exec(
        select(func.count(Story.id)).where(Story.created_at >= today_start)
    ).one()
    
    stats = {
        "total": total,
        "completed": completed,
        "failed": failed,
        "today": today
    }
    
    return templates.TemplateResponse("admin/stories.html", {
        "request": request,
        "stories": stories,
        "stats": stats,
        "current_user": current_user
    })


@router.delete("/api/story/{story_id}")
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete a story and all its chapters."""
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story_title = story.title
    
    # Delete chapters
    from sqlalchemy import delete
    session.exec(delete(Chapter).where(Chapter.story_id == story_id))
    
    # Delete carbon emissions for this story
    session.exec(delete(CarbonEmission).where(CarbonEmission.story_id == story_id))
    
    # Delete story
    session.delete(story)
    session.commit()
    
    logger.info(f"Admin {current_user.email} deleted story '{story_title}'")
    
    return {"status": "success"}


# ============================================================
# LOGS VIEWER
# ============================================================

@router.get("/logs")
async def admin_logs_page(
    request: Request,
    current_user: User = Depends(get_admin_user)
):
    """Logs viewer page."""
    logs_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_files = []
    
    if logs_dir.exists():
        for f in sorted(logs_dir.iterdir(), reverse=True):
            if f.is_file() and f.suffix == ".log":
                stat = f.stat()
                log_files.append({
                    "name": f.name,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
    
    return templates.TemplateResponse("admin/logs.html", {
        "request": request,
        "log_files": log_files,
        "current_user": current_user
    })


@router.get("/api/logs/{filename}")
async def get_log_content(
    filename: str,
    lines: int = 200,
    current_user: User = Depends(get_admin_user)
):
    """Get log file content (last N lines)."""
    logs_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_path = logs_dir / filename
    
    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    # Read last N lines
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            content = "".join(all_lines[-lines:])
        
        return {
            "filename": filename,
            "total_lines": len(all_lines),
            "showing_lines": min(lines, len(all_lines)),
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log: {str(e)}")
