"""
db.py — PostgreSQL connection wrapper and project schema.

DB wraps a psycopg2 connection:
    - query / query_one  → SELECT, returns dict rows (RealDictCursor)
    - execute / executemany → INSERT/UPDATE/DELETE, auto-commit
    - a failed statement auto-rolls-back so the connection stays usable
    - __init__ creates the project schema (영양성분DB, 영양소조건)

Connection settings come from DB_CONFIG (env vars with sensible defaults):

    export DB_HOST=localhost DB_NAME=textbook DB_USER=postgres DB_PASSWORD=dbclass

Usage:
    from db import get_db
    db = get_db(reset=True)            # connect + (re)create schema
    db.query_one("SELECT * FROM 영양성분db WHERE 식품명 = %s", ("김밥",))
"""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME", "textbook"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "dbclass"),
}


class DB:
    # Schema created on init. CREATE ... IF NOT EXISTS preserves existing data.
    SCHEMA = [
        """CREATE TABLE IF NOT EXISTS 영양성분DB (
            식품명   VARCHAR(50) PRIMARY KEY,
            에너지   FLOAT,
            단백질   FLOAT,
            지방     FLOAT,
            탄수화물 FLOAT,
            나트륨   FLOAT
        )""",
        """CREATE TABLE IF NOT EXISTS 영양소조건 (
            성별        VARCHAR(50),
            연령대_하한  INT,
            연령대_상한  INT,
            에너지      FLOAT,
            단백질      FLOAT,
            지방        FLOAT,
            탄수화물    FLOAT,
            나트륨      FLOAT,
            -- (성별, 연령대) 조합당 1행 → 중복 INSERT 방지
            PRIMARY KEY (성별, 연령대_하한, 연령대_상한)
        )""",
    ]
    TABLES = ["영양성분DB", "영양소조건"]

    def __init__(self, init=True, reset=False, **conn_params):
        self.conn = psycopg2.connect(**conn_params)
        if init or reset:
            self.init_db(reset=reset)

    @contextmanager
    def _cursor(self, commit=False, dict_rows=False):
        """Yield a cursor; commit on success, rollback on error (keeps conn usable)."""
        cur = self.conn.cursor(
            cursor_factory=RealDictCursor if dict_rows else None)
        try:
            yield cur
            if commit:
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def init_db(self, reset=False):
        """Create the schema. reset=True drops the tables first (clean rebuild)."""
        with self._cursor(commit=True) as cur:
            if reset:
                for table in self.TABLES:
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            for ddl in self.SCHEMA:
                cur.execute(ddl)

    def query(self, sql, params=None):
        with self._cursor(dict_rows=True) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql, params=None):
        with self._cursor(dict_rows=True) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def execute(self, sql, params=None):
        with self._cursor(commit=True) as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def executemany(self, sql, rows):
        with self._cursor(commit=True) as cur:
            cur.executemany(sql, rows)
            return cur.rowcount

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.close()


def get_db(reset=False, init=True, **overrides):
    """Connect using DB_CONFIG (overridable) and initialize the schema."""
    return DB(init=init, reset=reset, **{**DB_CONFIG, **overrides})


if __name__ == "__main__":
    # Smoke test
    db = get_db()
    print("DB connection OK. Tables:",
          [r["table_name"] for r in db.query(
              "SELECT table_name FROM information_schema.tables "
              "WHERE table_schema='public' ORDER BY table_name")])
    db.close()
