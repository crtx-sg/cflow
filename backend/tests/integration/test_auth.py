"""Integration tests for authentication endpoints."""

import pytest
from tests.conftest import auth_headers


@pytest.mark.asyncio
class TestLogin:
    """Tests for login endpoint."""

    async def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "admin123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, admin_user):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@test.com", "password": "password"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestMe:
    """Tests for current user endpoint."""

    async def test_me_authenticated(self, client, admin_token):
        """Test getting current user when authenticated."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    async def test_me_unauthenticated(self, client):
        """Test getting current user when not authenticated."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestLogout:
    """Tests for logout endpoint."""

    async def test_logout_success(self, client, admin_token):
        """Test successful logout."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
