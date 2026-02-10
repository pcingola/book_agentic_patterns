"""User authentication module with JSON-based user database."""

import hashlib
import json
import secrets
import string
from pathlib import Path

from pydantic import BaseModel


class User(BaseModel):
    """User model."""

    username: str
    password_hash: str
    role: str = "user"


class UserDatabase:
    """Simple JSON-based user database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_users({})

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _load_users(self) -> dict[str, User]:
        with open(self.db_path, "r") as f:
            data = json.load(f)
        return {username: User(**user_data) for username, user_data in data.items()}

    def _normalize_username(self, username: str) -> str:
        if "@" in username:
            return username.lower()
        return username

    def _save_users(self, users: dict[str, User]):
        data = {username: user.model_dump() for username, user in users.items()}
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_user(self, username: str, password: str, role: str = "user") -> bool:
        """Add a new user. Returns True if successful, False if user exists."""
        username = self._normalize_username(username)
        users = self._load_users()
        if username in users:
            return False
        users[username] = User(
            username=username, password_hash=self._hash_password(password), role=role
        )
        self._save_users(users)
        return True

    def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate user. Returns User if successful, None otherwise."""
        username = self._normalize_username(username)
        users = self._load_users()
        user = users.get(username)
        if user and user.password_hash == self._hash_password(password):
            return user
        return None

    def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> bool:
        """Change user password. Returns True if successful."""
        username = self._normalize_username(username)
        if not self.authenticate(username, old_password):
            return False
        users = self._load_users()
        users[username].password_hash = self._hash_password(new_password)
        self._save_users(users)
        return True

    def delete_user(self, username: str) -> bool:
        """Delete a user. Returns True if successful, False if user doesn't exist."""
        username = self._normalize_username(username)
        users = self._load_users()
        if username not in users:
            return False
        del users[username]
        self._save_users(users)
        return True

    def get_user(self, username: str) -> User | None:
        username = self._normalize_username(username)
        users = self._load_users()
        return users.get(username)

    def list_users(self) -> list[str]:
        users = self._load_users()
        return list(users.keys())


def generate_password(length: int = 16) -> str:
    """Generate a random password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
