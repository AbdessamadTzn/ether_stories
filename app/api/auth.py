from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import User, UserCreate, UserRead, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.logger import get_logger, log_error

logger = get_logger("auth")
router = APIRouter()

# 1. Signup Endpoint
@router.post("/signup", response_model=UserRead)
def signup(user: UserCreate, session: Session = Depends(get_session)):
    # Check if email exists
    statement = select(User).where(User.email == user.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        logger.warning(f"Signup attempt with existing email: {user.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    db_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        role=UserRole.USER # Default role
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    logger.info(f"New user registered: {user.email} (id: {db_user.id})")
    return db_user

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):

    statement = select(User).where(User.email == form_data.username)
    user = session.exec(statement).first()
    

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create Token with role included
    access_token = create_access_token(data={
        "sub": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else user.role
    })
    logger.info(f"User logged in: {user.email} (id: {user.id}, role: {user.role})")
    return {"access_token": access_token, "token_type": "bearer"}