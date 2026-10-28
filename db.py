"""数据访问层：连接、建表、事务。所有 SQL 一律参数化。"""
import sqlite3
from contextlib import contextmanager

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    coins         INTEGER NOT NULL DEFAULT 1000 CHECK (coins >= 0),
    pity_count    INTEGER NOT NULL DEFAULT 0,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    last_checkin  TEXT,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    rarity      INTEGER NOT NULL CHECK (rarity BETWEEN 1 AND 5),
    emoji       TEXT    NOT NULL DEFAULT '',
    image       TEXT,
    description TEXT    NOT NULL DEFAULT '',
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS draws (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    card_id    INTEGER NOT NULL REFERENCES cards(id),
    batch_id   TEXT    NOT NULL,
    is_pity    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS collections (
    user_id  INTEGER NOT NULL REFERENCES users(id),
    card_id  INTEGER NOT NULL REFERENCES cards(id),
    count    INTEGER NOT NULL DEFAULT 1,
    first_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, card_id)
);

CREATE TABLE IF NOT EXISTS app_config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_draws_user ON draws(user_id, created_at);
"""


def connect(path):
    """isolation_level=None 表示自动提交，事务由 transaction() 显式控制。"""
    conn = sqlite3.connect(path, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close_db(e=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_schema(conn):
    conn.executescript(SCHEMA)


@contextmanager
def transaction(conn):
    """BEGIN IMMEDIATE 抢占写锁，防止并发抽卡时余额竞态。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
