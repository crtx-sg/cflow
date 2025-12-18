"""File system security utilities."""

import re
import shlex
from pathlib import Path


class SecurityError(Exception):
    """Security-related error."""

    pass


class PathValidationError(SecurityError):
    """Path validation failed."""

    pass


def validate_path(path: str | Path, allowed_root: str | Path) -> Path:
    """Validate that a path is within the allowed root directory.

    Args:
        path: The path to validate
        allowed_root: The root directory that path must be within

    Returns:
        The canonicalized path

    Raises:
        PathValidationError: If path is outside allowed root or invalid
    """
    try:
        # Convert to Path objects and resolve to canonical paths
        canonical_path = Path(path).resolve()
        canonical_root = Path(allowed_root).resolve()

        # Check if path is relative to root (prevents traversal)
        if not canonical_path.is_relative_to(canonical_root):
            raise PathValidationError(
                f"Path '{path}' is outside allowed root '{allowed_root}'"
            )

        return canonical_path

    except (ValueError, OSError) as e:
        raise PathValidationError(f"Invalid path '{path}': {e}")


def validate_file_path(file_path: str) -> str:
    """Validate a file path string for safety.

    Args:
        file_path: Relative file path (e.g., "proposal.md", "specs/auth/spec.md")

    Returns:
        Sanitized file path

    Raises:
        PathValidationError: If path contains dangerous patterns
    """
    # Check for path traversal attempts
    if ".." in file_path:
        raise PathValidationError("Path traversal (..) not allowed")

    # Check for absolute paths
    if file_path.startswith("/") or (len(file_path) > 1 and file_path[1] == ":"):
        raise PathValidationError("Absolute paths not allowed")

    # Check for null bytes
    if "\x00" in file_path:
        raise PathValidationError("Null bytes not allowed in path")

    # Normalize path separators
    normalized = file_path.replace("\\", "/")

    # Remove leading/trailing whitespace and slashes
    normalized = normalized.strip().strip("/")

    # Validate characters (allow alphanumeric, -, _, ., /)
    if not re.match(r"^[\w\-./]+$", normalized):
        raise PathValidationError(f"Invalid characters in path: {file_path}")

    return normalized


def sanitize_cli_arg(arg: str) -> str:
    """Sanitize a CLI argument to prevent command injection.

    Args:
        arg: The argument to sanitize

    Returns:
        Sanitized argument safe for shell execution

    Raises:
        SecurityError: If argument contains dangerous patterns
    """
    # Check for shell metacharacters
    dangerous_chars = [";", "&", "|", "$", "`", "(", ")", "{", "}", "<", ">", "\n", "\r"]
    for char in dangerous_chars:
        if char in arg:
            raise SecurityError(f"Dangerous character '{char}' in argument")

    # Use shlex.quote for additional safety
    return shlex.quote(arg)


def validate_project_directory(path: str | Path) -> Path:
    """Validate that a project directory exists and is accessible.

    Args:
        path: Path to project directory

    Returns:
        Validated Path object

    Raises:
        PathValidationError: If directory doesn't exist or isn't accessible
    """
    try:
        project_path = Path(path).resolve()

        if not project_path.exists():
            raise PathValidationError(f"Directory does not exist: {path}")

        if not project_path.is_dir():
            raise PathValidationError(f"Path is not a directory: {path}")

        # Check if we can list the directory (read access)
        list(project_path.iterdir())

        return project_path

    except PermissionError:
        raise PathValidationError(f"Permission denied: {path}")
    except OSError as e:
        raise PathValidationError(f"Cannot access directory '{path}': {e}")


def ensure_directory(path: str | Path, allowed_root: str | Path) -> Path:
    """Ensure a directory exists within the allowed root.

    Args:
        path: Directory path to create
        allowed_root: Root directory that path must be within

    Returns:
        The created/existing directory path

    Raises:
        PathValidationError: If path is outside allowed root
    """
    canonical_path = validate_path(path, allowed_root)
    canonical_path.mkdir(parents=True, exist_ok=True)
    return canonical_path
