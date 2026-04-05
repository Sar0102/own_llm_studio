"""
Chat Store — персистентное хранилище сессий и сообщений в SQLite.
Паттерн: Repository + единая точка инициализации БД.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# БД рядом с бэкендом, не в tmp
DB_PATH = Path(__file__).parent.parent / "chats.db"


# ─── Domain models ────────────────────────────────────────────────────────────

@dataclass
class Message:
    role: str
    content: str
    id: Optional[int] = None
    session_id: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Session:
    id: str
    title: str
    created_at: str
    updated_at: str
    summary: str = ""
    messages: list[Message] = field(default_factory=list)


@dataclass
class Settings:
    """Пользовательские настройки приложения."""
    models_dir: str   = "~/Library/Application Support/LM Studio/models"
    n_ctx: int        = 8192
    n_gpu_layers: int = -1
    temperature: float = 0.7
    max_tokens: int   = 2048
    top_p: float      = 0.95
    top_k: int        = 40
    repeat_penalty: float = 1.1
    system_prompt: str = ""

    def to_dict(self) -> dict:
        return {
            "models_dir":     self.models_dir,
            "n_ctx":          self.n_ctx,
            "n_gpu_layers":   self.n_gpu_layers,
            "temperature":    self.temperature,
            "max_tokens":     self.max_tokens,
            "top_p":          self.top_p,
            "top_k":          self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "system_prompt":  self.system_prompt,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        return cls(
            models_dir    = d.get("models_dir",     cls.models_dir),
            n_ctx         = int(d.get("n_ctx",       cls.n_ctx)),
            n_gpu_layers  = int(d.get("n_gpu_layers", cls.n_gpu_layers)),
            temperature   = float(d.get("temperature", cls.temperature)),
            max_tokens    = int(d.get("max_tokens",  cls.max_tokens)),
            top_p         = float(d.get("top_p",     cls.top_p)),
            top_k         = int(d.get("top_k",       cls.top_k)),
            repeat_penalty= float(d.get("repeat_penalty", cls.repeat_penalty)),
            system_prompt = d.get("system_prompt",   cls.system_prompt),
        )


# ─── DB init ──────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Возвращает соединение с WAL-режимом для конкурентного доступа."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """
    Создаёт таблицы при первом запуске.
    Идемпотентна — безопасно вызывать при каждом старте.
    """
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL DEFAULT 'New chat',
                summary    TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role       TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);

            -- key-value таблица настроек: одна строка на параметр
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        # Миграция: summary в sessions
        cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
        if "summary" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN summary TEXT NOT NULL DEFAULT ''")

        # Вставляем дефолтные настройки если таблица пустая
        _insert_default_settings(conn)


def _insert_default_settings(conn: sqlite3.Connection) -> None:
    """
    Заполняет таблицу settings дефолтными значениями.
    Использует INSERT OR IGNORE — не перезаписывает существующие значения.
    """
    defaults = Settings()
    for key, value in defaults.to_dict().items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Repository ───────────────────────────────────────────────────────────────

class SessionRepository:
    """
    CRUD для сессий и сообщений.
    Все методы синхронные — FastAPI вызывает их через run_in_executor
    чтобы не блокировать event loop.
    """

    def list_sessions(self) -> list[Session]:
        """Возвращает все сессии без сообщений, отсортированные по updated_at desc."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [Session(**dict(r)) for r in rows]

    def get_session(self, session_id: str) -> Optional[Session]:
        """Возвращает сессию со всеми сообщениями."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None

            msg_rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()

        session = Session(**dict(row))
        session.messages = [Message(**dict(m)) for m in msg_rows]
        return session

    def create_session(self, session_id: str, title: str = "New chat") -> Session:
        """Создаёт новую пустую сессию."""
        now = _now()
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?,?,?,?)",
                (session_id, title, now, now),
            )
        return Session(id=session_id, title=title, created_at=now, updated_at=now)

    def update_title(self, session_id: str, title: str) -> None:
        """Обновляет заголовок сессии."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET title=?, updated_at=? WHERE id=?",
                (title, _now(), session_id),
            )

    def delete_session(self, session_id: str) -> None:
        """Удаляет сессию и все её сообщения (CASCADE)."""
        with get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def append_message(self, session_id: str, role: str, content: str) -> Message:
        """
        Добавляет сообщение в сессию и обновляет updated_at.
        Если сессии нет — создаёт автоматически.
        """
        now = _now()
        with get_connection() as conn:
            # Upsert сессии если не существует
            conn.execute(
                """INSERT INTO sessions (id, title, created_at, updated_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at""",
                (session_id, "New chat", now, now),
            )
            cursor = conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
                (session_id, role, content, now),
            )
            msg_id = cursor.lastrowid

        return Message(id=msg_id, session_id=session_id, role=role, content=content, created_at=now)

    def update_session_title_from_messages(self, session_id: str) -> None:
        """Устанавливает заголовок = первые 42 символа первого user-сообщения."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT content FROM messages WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",
                (session_id,),
            ).fetchone()
            if row:
                title = row["content"][:42]
                conn.execute(
                    "UPDATE sessions SET title=? WHERE id=?",
                    (title, session_id),
                )

    def update_summary(self, session_id: str, summary: str) -> None:
        """
        Сохраняет обновлённый summary в сессию.
        Вызывается после каждого ответа если контекст был сжат.
        """
        with get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET summary=?, updated_at=? WHERE id=?",
                (summary, _now(), session_id),
            )

    def get_summary(self, session_id: str) -> str:
        """Возвращает текущий summary сессии."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT summary FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
        return row["summary"] if row else ""


class SettingsRepository:
    """
    CRUD для пользовательских настроек.
    Хранит настройки как key-value пары в таблице settings.
    Дефолтные значения определены в dataclass Settings.
    """

    def load(self) -> Settings:
        """
        Загружает все настройки из БД.
        Недостающие ключи заполняются дефолтами из Settings.
        """
        with get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()

        data = {r["key"]: r["value"] for r in rows}
        return Settings.from_dict(data)

    def save(self, settings: Settings) -> None:
        """
        Сохраняет все настройки.
        INSERT OR REPLACE — обновляет существующие, создаёт новые.
        """
        with get_connection() as conn:
            for key, value in settings.to_dict().items():
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, str(value)),
                )

    def update(self, key: str, value: str) -> None:
        """Обновляет одну настройку по ключу."""
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )


# Глобальные репозитории
session_repo  = SessionRepository()
settings_repo = SettingsRepository()
