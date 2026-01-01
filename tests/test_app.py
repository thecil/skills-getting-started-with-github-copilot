"""
Tests for the Mergington High School Activities API
"""

import pytest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, activity in activities.items():
        activity["participants"] = original_activities[name]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have activities
        assert len(data) > 0
        
        # Check required fields in each activity
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
    
    def test_get_activities_includes_basketball_team(self, client, reset_activities):
        """Test that Basketball Team is in the activities list"""
        response = client.get("/activities")
        data = response.json()
        
        assert "Basketball Team" in data
        assert data["Basketball Team"]["max_participants"] == 15


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer%20Club/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "test@mergington.edu" in activities["Soccer Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client, reset_activities):
        """Test signup fails for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_email(self, client, reset_activities):
        """Test that duplicate signup is rejected"""
        activity_name = "Basketball Team"
        email = "james@mergington.edu"  # Already signed up for Basketball Team
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_url_encoded_email(self, client, reset_activities):
        """Test signup with URL-encoded email"""
        response = client.post(
            "/activities/Drama%20Club/signup?email=newstudent%40mergington.edu"
        )
        
        assert response.status_code == 200
        assert "newstudent@mergington.edu" in activities["Drama Club"]["participants"]


class TestUnregister:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        activity_name = "Basketball Team"
        email = "james@mergington.edu"  # Already signed up
        
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify participant was removed
        assert email not in activities[activity_name]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister fails for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_not_signed_up(self, client, reset_activities):
        """Test unregister fails when student not signed up"""
        response = client.post(
            "/activities/Art%20Studio/unregister?email=notreal@mergington.edu"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        activity_name = "Soccer Club"
        email = "alex@mergington.edu"
        
        # Verify participant is initially there
        assert email in activities[activity_name]["participants"]
        
        # Unregister
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        assert response.status_code == 200
        
        # Verify participant is gone
        assert email not in activities[activity_name]["participants"]


class TestIntegration:
    """Integration tests for signup and unregister flows"""
    
    def test_signup_then_unregister_flow(self, client, reset_activities):
        """Test signing up then unregistering from an activity"""
        activity_name = "Chess Club"
        new_email = "newplayer@mergington.edu"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup?email={new_email}"
        )
        assert signup_response.status_code == 200
        assert new_email in activities[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity_name}/unregister?email={new_email}"
        )
        assert unregister_response.status_code == 200
        assert new_email not in activities[activity_name]["participants"]
    
    def test_multiple_signups_same_activity(self, client, reset_activities):
        """Test multiple different students signing up for same activity"""
        activity_name = "Debate Team"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup?email={email}"
            )
            assert response.status_code == 200
            assert email in activities[activity_name]["participants"]
        
        # Verify all students are signed up
        for email in emails:
            assert email in activities[activity_name]["participants"]
