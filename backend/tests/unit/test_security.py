"""Unit tests for security utilities."""

import pytest
from datetime import timedelta

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
)


class TestPasswordHashing:
    """Tests for password hashing."""

    def test_hash_password(self):
        """Test password hashing creates different hash each time."""
        password = "mysecretpassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != password
        assert hash2 != password
        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self):
        """Test creating access token."""
        token = create_access_token(subject=1)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test creating access token with custom expiry."""
        token = create_access_token(
            subject=1,
            expires_delta=timedelta(hours=1)
        )

        assert token is not None
        assert isinstance(token, str)
