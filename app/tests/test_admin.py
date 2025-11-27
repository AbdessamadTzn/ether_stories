"""
Admin Panel Tests
=================
Tests for admin dashboard, user management, and story management.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.db.models import User, Story, UserRole


class TestAdminAccess:
    """Test admin access control."""
    
    def test_admin_dashboard_requires_auth(self, client: TestClient):
        """Test that admin dashboard requires authentication."""
        response = client.get("/admin")
        # Should redirect or return 401/403
        assert response.status_code in [401, 403, 307]
    
    def test_admin_dashboard_requires_admin_role(self, auth_client: TestClient):
        """Test that regular users cannot access admin dashboard."""
        response = auth_client.get("/admin")
        assert response.status_code == 403
    
    def test_admin_dashboard_accessible_by_admin(self, admin_client: TestClient):
        """Test that admin users can access dashboard."""
        response = admin_client.get("/admin")
        assert response.status_code == 200
    
    def test_admin_users_page_requires_admin(self, auth_client: TestClient):
        """Test that users page requires admin role."""
        response = auth_client.get("/admin/users")
        assert response.status_code == 403
    
    def test_admin_stories_page_requires_admin(self, auth_client: TestClient):
        """Test that stories page requires admin role."""
        response = auth_client.get("/admin/stories")
        assert response.status_code == 403


class TestAdminUserManagement:
    """Test admin user management functionality."""
    
    def test_get_user_details(self, admin_client: TestClient, test_user: User):
        """Test fetching user details via API."""
        response = admin_client.get(f"/admin/api/user/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert "story_count" in data
        assert "co2_grams" in data
    
    def test_get_nonexistent_user(self, admin_client: TestClient):
        """Test fetching non-existent user returns 404."""
        response = admin_client.get("/admin/api/user/99999")
        assert response.status_code == 404
    
    def test_update_user(self, admin_client: TestClient, test_user: User, session: Session):
        """Test updating user details."""
        response = admin_client.put(
            f"/admin/api/user/{test_user.id}",
            json={
                "email": test_user.email,
                "full_name": "Updated Name",
                "role": "writer",
                "is_active": True
            }
        )
        assert response.status_code == 200
        
        # Verify update
        session.refresh(test_user)
        assert test_user.full_name == "Updated Name"
        assert test_user.role == UserRole.WRITER
    
    def test_update_user_role_to_admin(self, admin_client: TestClient, test_user: User, session: Session):
        """Test promoting user to admin."""
        response = admin_client.put(
            f"/admin/api/user/{test_user.id}",
            json={
                "email": test_user.email,
                "full_name": test_user.full_name,
                "role": "admin",
                "is_active": True
            }
        )
        assert response.status_code == 200
        session.refresh(test_user)
        assert test_user.role == UserRole.ADMIN
    
    def test_deactivate_user(self, admin_client: TestClient, test_user: User, session: Session):
        """Test deactivating a user account."""
        response = admin_client.put(
            f"/admin/api/user/{test_user.id}",
            json={
                "email": test_user.email,
                "full_name": test_user.full_name,
                "role": "user",
                "is_active": False
            }
        )
        assert response.status_code == 200
        session.refresh(test_user)
        assert test_user.is_active == False
    
    def test_delete_user(self, admin_client: TestClient, session: Session):
        """Test deleting a user."""
        # Create a user to delete
        from app.core.security import hash_password
        user_to_delete = User(
            email="delete_me@ether.com",
            hashed_password=hash_password("password"),
            full_name="Delete Me",
            role=UserRole.USER,
            is_active=True
        )
        session.add(user_to_delete)
        session.commit()
        user_id = user_to_delete.id
        
        response = admin_client.delete(f"/admin/api/user/{user_id}")
        assert response.status_code == 200
        
        # Verify deletion
        deleted_user = session.get(User, user_id)
        assert deleted_user is None
    
    def test_cannot_delete_admin_user(self, admin_client: TestClient, session: Session):
        """Test that admin users cannot be deleted."""
        # Create another admin
        from app.core.security import hash_password
        other_admin = User(
            email="other_admin@ether.com",
            hashed_password=hash_password("password"),
            full_name="Other Admin",
            role=UserRole.ADMIN,
            is_active=True
        )
        session.add(other_admin)
        session.commit()
        
        response = admin_client.delete(f"/admin/api/user/{other_admin.id}")
        assert response.status_code == 400
        assert "admin" in response.json()["detail"].lower()


class TestAdminStoryManagement:
    """Test admin story management functionality."""
    
    def test_admin_stories_page(self, admin_client: TestClient, test_story: Story):
        """Test stories management page loads."""
        response = admin_client.get("/admin/stories")
        assert response.status_code == 200
    
    def test_delete_story(self, admin_client: TestClient, test_story: Story, session: Session):
        """Test deleting a story."""
        story_id = test_story.id
        
        response = admin_client.delete(f"/admin/api/story/{story_id}")
        assert response.status_code == 200
        
        # Verify deletion
        deleted_story = session.get(Story, story_id)
        assert deleted_story is None
    
    def test_delete_nonexistent_story(self, admin_client: TestClient):
        """Test deleting non-existent story returns 404."""
        response = admin_client.delete("/admin/api/story/99999")
        assert response.status_code == 404


class TestAdminLogs:
    """Test admin logs functionality."""
    
    def test_logs_page_accessible(self, admin_client: TestClient):
        """Test logs page is accessible to admin."""
        response = admin_client.get("/admin/logs")
        assert response.status_code == 200
    
    def test_logs_page_requires_admin(self, auth_client: TestClient):
        """Test logs page requires admin role."""
        response = auth_client.get("/admin/logs")
        assert response.status_code == 403
