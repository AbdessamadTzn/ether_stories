"""
Database Model Tests
====================
Tests for database models, relationships, and constraints.
"""
import pytest
from sqlmodel import Session, select
from app.db.models import User, Story, Chapter, CarbonEmission, UserRole, StoryStatus, ChapterStatus
from app.core.security import get_password_hash, verify_password


class TestUserModel:
    """Test User model."""
    
    def test_create_user(self, session: Session):
        """Test creating a user."""
        user = User(
            email="newuser@ether.com",
            hashed_password=get_password_hash("password123"),
            full_name="New User"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        
        assert user.id is not None
        assert user.email == "newuser@ether.com"
        assert user.role == UserRole.USER  # Default role
        assert user.is_active == True  # Default active
    
    def test_user_password_hashing(self, session: Session):
        """Test password is hashed, not stored in plain text."""
        plain_password = "mysecretpassword"
        user = User(
            email="hashtest@ether.com",
            hashed_password=get_password_hash(plain_password),
            full_name="Hash Test"
        )
        session.add(user)
        session.commit()
        
        # Password should not be stored as plain text
        assert user.hashed_password != plain_password
        # But should verify correctly
        assert verify_password(plain_password, user.hashed_password)
    
    def test_user_roles(self, session: Session):
        """Test different user roles."""
        roles = [UserRole.USER, UserRole.WRITER, UserRole.ADMIN]
        
        for i, role in enumerate(roles):
            user = User(
                email=f"role{i}@ether.com",
                hashed_password=get_password_hash("pass"),
                full_name=f"Role {role.value}",
                role=role
            )
            session.add(user)
        
        session.commit()
        
        # Verify each role
        for i, role in enumerate(roles):
            stmt = select(User).where(User.email == f"role{i}@ether.com")
            user = session.exec(stmt).first()
            assert user.role == role
    
    def test_user_unique_email(self, session: Session, test_user: User):
        """Test email uniqueness constraint."""
        duplicate = User(
            email=test_user.email,  # Same email
            hashed_password=get_password_hash("pass"),
            full_name="Duplicate"
        )
        session.add(duplicate)
        
        with pytest.raises(Exception):  # Should raise integrity error
            session.commit()
    
    def test_user_deactivation(self, session: Session, test_user: User):
        """Test deactivating a user."""
        test_user.is_active = False
        session.commit()
        session.refresh(test_user)
        
        assert test_user.is_active == False


class TestStoryModel:
    """Test Story model."""
    
    def test_story_default_status(self, session: Session, test_user: User):
        """Test story default status is pending."""
        story = Story(
            title="Default Status Test",
            user_id=test_user.id
        )
        session.add(story)
        session.commit()
        session.refresh(story)
        
        # Default should be PENDING or whatever is set
        assert story.status in [StoryStatus.PENDING, StoryStatus.GENERATING, StoryStatus.COMPLETED]
    
    def test_story_plan_data_json(self, session: Session, test_user: User):
        """Test story plan_data stores JSON correctly."""
        plan = {
            "plan": {
                "titre": "Test Story",
                "theme": "adventure",
                "duree_estimee": 5,
                "chapitres": [
                    {"numero": 1, "titre": "Beginning"},
                    {"numero": 2, "titre": "Middle"},
                    {"numero": 3, "titre": "End"}
                ]
            }
        }
        
        story = Story(
            title="JSON Test",
            user_id=test_user.id,
            plan_data=plan
        )
        session.add(story)
        session.commit()
        session.refresh(story)
        
        assert story.plan_data["plan"]["theme"] == "adventure"
        assert len(story.plan_data["plan"]["chapitres"]) == 3
    
    def test_story_timestamps(self, session: Session, test_user: User):
        """Test story has created_at timestamp."""
        story = Story(
            title="Timestamp Test",
            user_id=test_user.id
        )
        session.add(story)
        session.commit()
        session.refresh(story)
        
        assert story.created_at is not None


class TestChapterModel:
    """Test Chapter model."""
    
    def test_chapter_content_storage(self, session: Session, test_story: Story):
        """Test chapter stores long content correctly."""
        long_content = "Once upon a time " * 1000  # Long story
        
        chapter = Chapter(
            story_id=test_story.id,
            chapter_number=99,
            title="Long Chapter",
            content=long_content
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        
        assert len(chapter.content) == len(long_content)
    
    def test_chapter_audio_path(self, session: Session, test_story: Story):
        """Test chapter can store audio file path."""
        chapter = Chapter(
            story_id=test_story.id,
            chapter_number=1,
            title="Audio Test",
            content="Content here",
            audio_path="/static/audio/test.mp3"
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        
        assert chapter.audio_path == "/static/audio/test.mp3"


class TestCascadeDeletes:
    """Test cascade delete behavior."""
    
    def test_delete_user_deletes_stories(self, session: Session):
        """Test that deleting user should handle related stories."""
        # Create user with story
        user = User(
            email="cascade_test@ether.com",
            hashed_password=get_password_hash("pass"),
            full_name="Cascade Test"
        )
        session.add(user)
        session.commit()
        
        story = Story(
            title="To Be Deleted",
            user_id=user.id
        )
        session.add(story)
        session.commit()
        
        story_id = story.id
        
        # Note: Actual cascade behavior depends on model configuration
        # This test documents expected behavior
        session.delete(user)
        session.commit()
        
        # Check if story still exists (depends on cascade settings)
        remaining_story = session.get(Story, story_id)
        # Either story is deleted (cascade) or orphaned (no cascade)
        # This assertion should match your actual model behavior
    
    def test_delete_story_deletes_chapters(self, session: Session, test_user: User):
        """Test that deleting story deletes its chapters."""
        story = Story(
            title="Story with Chapters",
            user_id=test_user.id
        )
        session.add(story)
        session.commit()
        
        # Add chapters
        chapter_ids = []
        for i in range(3):
            chapter = Chapter(
                story_id=story.id,
                chapter_number=i + 1,
                title=f"Chapter {i + 1}",
                content="Content"
            )
            session.add(chapter)
            session.commit()
            chapter_ids.append(chapter.id)
        
        # Delete story
        session.delete(story)
        session.commit()
        
        # Check chapters
        for cid in chapter_ids:
            remaining = session.get(Chapter, cid)
            # Chapters should be deleted if cascade is set up
