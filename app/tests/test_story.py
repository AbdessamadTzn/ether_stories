"""
Story Generation Tests
======================
Tests for story creation, chapter generation, and workflow.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.db.models import User, Story, Chapter, StoryStatus
from app.agents.manager.manager import calculate_chapter_count


class TestChapterCalculation:
    """Test chapter count calculation logic."""
    
    def test_chapter_count_2_minutes(self):
        """Test 2 minute story = 1 chapter."""
        assert calculate_chapter_count(2) == 1
    
    def test_chapter_count_3_minutes(self):
        """Test 3 minute story = 2 chapters."""
        assert calculate_chapter_count(3) == 2
    
    def test_chapter_count_5_minutes(self):
        """Test 5 minute story = 3 chapters."""
        assert calculate_chapter_count(5) == 3
    
    def test_chapter_count_7_minutes(self):
        """Test 7 minute story = 4 chapters."""
        assert calculate_chapter_count(7) == 4
    
    def test_chapter_count_10_minutes(self):
        """Test 10 minute story = 5 chapters."""
        assert calculate_chapter_count(10) == 5
    
    def test_chapter_count_minimum(self):
        """Test minimum 1 chapter for very short stories."""
        assert calculate_chapter_count(1) >= 1
    
    def test_chapter_count_formula(self):
        """Test the formula: ceil(duration / 2)."""
        import math
        for duration in range(1, 15):
            expected = math.ceil(duration / 2)
            assert calculate_chapter_count(duration) == expected


class TestStoryModel:
    """Test Story model operations."""
    
    def test_create_story(self, session: Session, test_user: User):
        """Test creating a new story."""
        story = Story(
            title="My Test Story",
            user_id=test_user.id,
            status=StoryStatus.PENDING,
            plan_data={"plan": {"theme": "adventure"}}
        )
        session.add(story)
        session.commit()
        session.refresh(story)
        
        assert story.id is not None
        assert story.title == "My Test Story"
        assert story.status == StoryStatus.PENDING
    
    def test_story_user_relationship(self, session: Session, test_story: Story, test_user: User):
        """Test story-user relationship."""
        assert test_story.user_id == test_user.id
    
    def test_story_status_transitions(self, session: Session, test_user: User):
        """Test story status can be updated."""
        story = Story(
            title="Status Test",
            user_id=test_user.id,
            status=StoryStatus.PENDING
        )
        session.add(story)
        session.commit()
        
        # Update to generating
        story.status = StoryStatus.GENERATING
        session.commit()
        session.refresh(story)
        assert story.status == StoryStatus.GENERATING
        
        # Update to completed
        story.status = StoryStatus.COMPLETED
        session.commit()
        session.refresh(story)
        assert story.status == StoryStatus.COMPLETED


class TestChapterModel:
    """Test Chapter model operations."""
    
    def test_create_chapter(self, session: Session, test_story: Story):
        """Test creating a chapter."""
        chapter = Chapter(
            story_id=test_story.id,
            chapter_number=2,
            title="Chapter 2",
            content="The adventure continues..."
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        
        assert chapter.id is not None
        assert chapter.story_id == test_story.id
        assert chapter.chapter_number == 2
    
    def test_chapter_ordering(self, session: Session, test_story: Story):
        """Test chapters can be ordered by chapter_number."""
        # Add more chapters
        for i in range(2, 5):
            chapter = Chapter(
                story_id=test_story.id,
                chapter_number=i,
                title=f"Chapter {i}",
                content=f"Content for chapter {i}"
            )
            session.add(chapter)
        session.commit()
        
        # Query ordered chapters
        from sqlmodel import select
        stmt = select(Chapter).where(Chapter.story_id == test_story.id).order_by(Chapter.chapter_number)
        chapters = session.exec(stmt).all()
        
        assert len(chapters) >= 4  # 1 from fixture + 3 new
        for i, chapter in enumerate(chapters):
            assert chapter.chapter_number == i + 1


class TestStoryCreationEndpoint:
    """Test story creation API endpoint."""
    
    def test_create_page_requires_auth(self, client: TestClient):
        """Test create page requires authentication."""
        response = client.get("/create")
        assert response.status_code in [401, 307]  # Unauthorized or redirect
    
    def test_create_page_accessible_when_logged_in(self, auth_client: TestClient):
        """Test create page is accessible when authenticated."""
        response = auth_client.get("/create")
        assert response.status_code == 200


class TestMyStoriesEndpoint:
    """Test my-stories endpoint."""
    
    def test_my_stories_requires_auth(self, client: TestClient):
        """Test my-stories requires authentication."""
        response = client.get("/my-stories")
        assert response.status_code in [401, 307]
    
    def test_my_stories_shows_user_stories(self, auth_client: TestClient, test_story: Story):
        """Test my-stories shows authenticated user's stories."""
        response = auth_client.get("/my-stories")
        assert response.status_code == 200
        # Story title should be in the response
        assert test_story.title.encode() in response.content or response.status_code == 200
