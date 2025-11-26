from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import User, UserCreate, UserRead, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()

# 1. Signup Endpoint
@router.post("/signup", response_model=UserRead)
def signup(user: UserCreate, session: Session = Depends(get_session)):
    # Check if email exists
    statement = select(User).where(User.email == user.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        # FIX 1: Fixed typo "registred" -> "registered"
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
    return db_user

# 2. Login Endpoint
@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    # OAuth2PasswordRequestForm stores email in 'username' field
    statement = select(User).where(User.email == form_data.username)
    user = session.exec(statement).first()
    
    # FIX 2: Changed 'hashed_password' to 'user.hashed_password'
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create Token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}