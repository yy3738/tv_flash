import hashlib
import secrets
import time
import uuid

import bcrypt

from .config import ADMIN_PASSWORD, ADMIN_USERNAME
from .db import db


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_admin():
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM sys_account WHERE deleted=1 LIMIT 1"
        ).fetchone()
        if row is not None:
            return
        now = int(time.time() * 1000)
        conn.execute(
            "INSERT INTO sys_account "
            "(id, username, password_hash, version, deleted, create_time, update_time) "
            "VALUES (?, ?, ?, 0, 1, ?, ?)",
            (uuid.uuid4().hex, ADMIN_USERNAME, hash_password(ADMIN_PASSWORD), now, now),
        )
