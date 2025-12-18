"""Unit tests for filesystem security utilities."""

import pytest
from pathlib import Path

from app.services.filesystem import (
    validate_path,
    validate_file_path,
    sanitize_cli_arg,
    PathValidationError,
    SecurityError,
)


class TestValidatePath:
    """Tests for path validation."""

    def test_valid_path_within_root(self, tmp_path):
        """Test valid path within allowed root."""
        allowed_root = tmp_path
        test_file = tmp_path / "subdir" / "file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()

        result = validate_path(test_file, allowed_root)
        assert result == test_file.resolve()

    def test_path_traversal_rejected(self, tmp_path):
        """Test path traversal is rejected."""
        allowed_root = tmp_path / "allowed"
        allowed_root.mkdir()
        outside_path = tmp_path / "allowed" / ".." / "outside"

        with pytest.raises(PathValidationError):
            validate_path(outside_path, allowed_root)

    def test_absolute_path_outside_root_rejected(self, tmp_path):
        """Test absolute path outside root is rejected."""
        allowed_root = tmp_path / "allowed"
        allowed_root.mkdir()

        with pytest.raises(PathValidationError):
            validate_path("/etc/passwd", allowed_root)


class TestValidateFilePath:
    """Tests for file path string validation."""

    def test_valid_simple_path(self):
        """Test valid simple file path."""
        result = validate_file_path("proposal.md")
        assert result == "proposal.md"

    def test_valid_nested_path(self):
        """Test valid nested file path."""
        result = validate_file_path("specs/auth/spec.md")
        assert result == "specs/auth/spec.md"

    def test_path_traversal_rejected(self):
        """Test path traversal is rejected."""
        with pytest.raises(PathValidationError):
            validate_file_path("../etc/passwd")

    def test_absolute_path_rejected(self):
        """Test absolute path is rejected."""
        with pytest.raises(PathValidationError):
            validate_file_path("/etc/passwd")

    def test_null_byte_rejected(self):
        """Test null byte is rejected."""
        with pytest.raises(PathValidationError):
            validate_file_path("file\x00.txt")

    def test_normalizes_backslashes(self):
        """Test backslashes are normalized to forward slashes."""
        result = validate_file_path("specs\\auth\\spec.md")
        assert result == "specs/auth/spec.md"

    def test_strips_leading_trailing_slashes(self):
        """Test leading/trailing slashes are stripped."""
        result = validate_file_path("/specs/auth/")
        assert result == "specs/auth"


class TestSanitizeCliArg:
    """Tests for CLI argument sanitization."""

    def test_safe_argument(self):
        """Test safe argument passes through (quoted)."""
        result = sanitize_cli_arg("simple-arg")
        assert "simple-arg" in result

    def test_semicolon_rejected(self):
        """Test semicolon is rejected."""
        with pytest.raises(SecurityError):
            sanitize_cli_arg("arg; rm -rf /")

    def test_pipe_rejected(self):
        """Test pipe is rejected."""
        with pytest.raises(SecurityError):
            sanitize_cli_arg("arg | cat /etc/passwd")

    def test_backtick_rejected(self):
        """Test backtick is rejected."""
        with pytest.raises(SecurityError):
            sanitize_cli_arg("arg `whoami`")

    def test_dollar_rejected(self):
        """Test dollar sign is rejected."""
        with pytest.raises(SecurityError):
            sanitize_cli_arg("arg $HOME")

    def test_ampersand_rejected(self):
        """Test ampersand is rejected."""
        with pytest.raises(SecurityError):
            sanitize_cli_arg("arg & background")
