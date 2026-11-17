import contextlib
import sqlite3

from .config import DATA_DIR, DB_PATH


@contextlib.contextmanager
def db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS sys_account (
  id            TEXT PRIMARY KEY,
  username      TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  state         TEXT DEFAULT 'enabled',
  version       INTEGER DEFAULT 0,
  deleted       INTEGER DEFAULT 1,
  create_time   INTEGER,
  update_time   INTEGER
);

CREATE TABLE IF NOT EXISTS biz_device (
  id          TEXT PRIMARY KEY,
  account_id  TEXT NOT NULL,
  name        TEXT,
  token_hash  TEXT NOT NULL UNIQUE,
  online      INTEGER DEFAULT 0,
  last_seen   INTEGER,
  version     INTEGER DEFAULT 0,
  deleted     INTEGER DEFAULT 1,
  create_time INTEGER,
  update_time INTEGER
);
CREATE INDEX IF NOT EXISTS idx_biz_device_account ON biz_device(account_id);

CREATE TABLE IF NOT EXISTS biz_session (
  id          TEXT PRIMARY KEY,
  device_id   TEXT NOT NULL,
  state       TEXT DEFAULT 'active',
  started_at  INTEGER,
  ended_at    INTEGER,
  version     INTEGER DEFAULT 0,
  deleted     INTEGER DEFAULT 1,
  create_time INTEGER,
  update_time INTEGER
);
CREATE INDEX IF NOT EXISTS idx_biz_session_device ON biz_session(device_id);
"""


def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)
