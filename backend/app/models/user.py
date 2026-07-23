from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlmodel import SQLModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=_uuid, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: Optional[str] = None
    provider: str = "email"                 # email | google | apple
    provider_uid: Optional[str] = None
    display_name: str
    role: str = "user"                      # user | moderator | admin
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Child(SQLModel, table=True):
    """Minimal child model included so the domain pattern is demonstrable."""
    __tablename__ = "children"

    id: str = Field(default_factory=_uuid, primary_key=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    name: Optional[str] = None
    due_date: Optional[datetime] = None
    birth_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
