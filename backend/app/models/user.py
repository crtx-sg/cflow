"""User model for authentication and authorization."""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUTHOR = "author"
    VIEWER = "viewer"


class UserBase(SQLModel):
    """Base user fields."""

    email: str = Field(unique=True, index=True)
    role: UserRole = Field(default=UserRole.AUTHOR)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    """User database model."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime | None = Field(default=None)


class UserCreate(SQLModel):
    """Schema for creating a user."""

    email: str
    password: str
    role: UserRole = UserRole.AUTHOR


class UserRead(UserBase):
    """Schema for reading a user."""

    id: int
    created_at: datetime
    last_login: datetime | None
