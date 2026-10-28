import os
import re
from contextlib import contextmanager
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor

DEFAULT_URL = "mysql+pymysql://clinic:clinic_pass@127.0.0.1:3306/clinic_crm"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL).strip()


def _connect_kwargs():
    raw = database_url()
    if raw.startswith("mysql+pymysql://"):
        raw = "mysql://" + raw[len("mysql+pymysql://") :]
    parsed = urlparse(raw)
    db = (parsed.path or "/clinic_crm").lstrip("/") or "clinic_crm"
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or "clinic"),
        "password": unquote(parsed.password or "clinic_pass"),
        "database": db,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }


@contextmanager
def db_conn():
    conn = pymysql.connect(**_connect_kwargs())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db_ping() -> bool:
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except pymysql.Error:
        return False
