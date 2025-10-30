import aiosqlite
from contextlib import asynccontextmanager
from typing import Iterable, Any, Optional
from pathlib import Path

from bot.config import settings

# гарантуємо існування папки під БД
Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._bootstrap()
        return self

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, sql: str, params: Iterable[Any] = ()):
        cur = await self._conn.execute(sql, params)
        await self._conn.commit()
        await cur.close()

    async def fetchone(self, sql: str, params: Iterable[Any] = ()):
        cur = await self._conn.execute(sql, params)
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, sql: str, params: Iterable[Any] = ()):
        cur = await self._conn.execute(sql, params)
        rows = await cur.fetchall()
        await cur.close()
        return rows

    @asynccontextmanager
    async def transaction(self):
        try:
            await self._conn.execute("BEGIN")
            yield self._conn
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise

    async def _bootstrap(self):
        await self.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            last_name   TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );""")
        await self.execute("""CREATE TABLE IF NOT EXISTS user_prefs (
            user_id INTEGER PRIMARY KEY,
            lang    TEXT NOT NULL
        );""")
        await self.execute("""CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_at TEXT DEFAULT (datetime('now'))
        );""")
        await self.execute("""CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );""")
        await self.execute("""CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            partner_id INTEGER NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
            note TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );""")
        await self.execute("""CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT (datetime('now')),
            link_slug TEXT,
            user_id INTEGER,
            ip TEXT,
            ref TEXT,
            ua TEXT,
            dest_url TEXT
        );""")
        await self.execute("""CREATE TABLE IF NOT EXISTS payouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount_usdt REAL,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );""")
        await self.execute("""CREATE TABLE IF NOT EXISTS leads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            destination TEXT,
            date_from   TEXT,
            date_to     TEXT,
            pax         INTEGER,
            budget      TEXT,
            notes       TEXT,
            status      TEXT DEFAULT 'new',
            link_slug   TEXT,
            partner_code TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );""")


# ⚠️ ЖОДНИХ імпортів звідси нагору!
# Створюємо синглтон БД — він буде імпортований як `from bot.db import db`
db = Database(settings.DB_PATH)
