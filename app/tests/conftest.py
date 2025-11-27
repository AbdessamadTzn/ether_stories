import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from app.main import app
from app.db.session import get_session
from app.db.models import User, Story, Chapter, CarbonEmission, UserRole, StoryStatus, ChapterStatus, OperationType
from app.core.security import get_password_hash
from datetime import datetime


TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)


@pytest.fixture(name="session")
def session_fixture():

    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session
    

    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    
    client = TestClient(app)
    yield client
    
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a regular test user."""
    user = User(
        email="testuser@ether.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        role=UserRole.USER,
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """Create an admin test user."""
    user = User(
        email="admin@ether.com",
        hashed_password=get_password_hash("adminpassword"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_story")
def test_story_fixture(session: Session, test_user: User):
    """Create a test story with chapters."""
    story = Story(
        title="Test Story",
        user_id=test_user.id,
        status=StoryStatus.COMPLETED,
        plan_data={"plan": {"duree_estimee": 5, "chapitres": []}}
    )
    session.add(story)
    session.commit()
    session.refresh(story)
    
    # Add a chapter
    chapter = Chapter(
        story_id=story.id,
        chapter_number=1,
        title="Chapter 1",
        content="Once upon a time...",
        status=ChapterStatus.COMPLETED
    )
    session.add(chapter)
    session.commit()
    
    return story


@pytest.fixture(name="test_carbon")
def test_carbon_fixture(session: Session, test_user: User, test_story: Story):
    """Create test carbon emission record."""
    emission = CarbonEmission(
        user_id=test_user.id,
        story_id=test_story.id,
        operation_type=OperationType.STORY_GENERATION,
        operation_details="Test story generation",
        emissions_kg=0.001,
        energy_kwh=0.005,
        duration_seconds=10.5
    )
    session.add(emission)
    session.commit()
    session.refresh(emission)
    return emission


@pytest.fixture(name="auth_client")
def auth_client_fixture(client: TestClient, test_user: User):
    """Client with authentication cookie for regular user."""
    # Login to get token
    response = client.post(
        "/auth/login",
        data={"username": "testuser@ether.com", "password": "testpassword"}
    )
    return client


@pytest.fixture(name="admin_client")
def admin_client_fixture(client: TestClient, admin_user: User):
    """Client with authentication cookie for admin user."""
    response = client.post(
        "/auth/login",
        data={"username": "admin@ether.com", "password": "adminpassword"}
    )
    return client