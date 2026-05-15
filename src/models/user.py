# src/models/user.py
from datetime import datetime
from typing import Optional

class User:
    def __init__(
        self,
        id: str = None,
        email: str = None,
        name: str = None,
        role: str = "user",
        google_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.google_id = google_id
        self.created_at = created_at if created_at else datetime.utcnow()
        self.last_login_at = last_login_at
        self.is_active = is_active

    def __repr__(self):
        return f"User(id={self.id}, email={self.email}, name={self.name}, role={self.role})"