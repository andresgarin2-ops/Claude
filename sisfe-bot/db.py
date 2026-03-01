"""
Base de datos SQLite para persistir el estado de los expedientes.
"""

import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS expediente_states (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo           TEXT    NOT NULL,
                    hash             TEXT    NOT NULL,
                    content_preview  TEXT,
                    last_movement    TEXT,
                    checked_at       TEXT    NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_codigo
                    ON expediente_states(codigo);
            """)

    def get_last_state(self, codigo: str) -> dict | None:
        """Devuelve el último estado guardado para un expediente, o None si es nuevo."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM expediente_states "
                "WHERE codigo = ? ORDER BY checked_at DESC LIMIT 1",
                (codigo,),
            ).fetchone()
        return dict(row) if row else None

    def save_state(self, codigo: str, state: dict):
        """Guarda un nuevo snapshot del estado de un expediente."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO expediente_states "
                "(codigo, hash, content_preview, last_movement, checked_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    codigo,
                    state["hash"],
                    state.get("content_preview", ""),
                    state.get("last_movement", ""),
                    state.get("timestamp", datetime.now().isoformat()),
                ),
            )

    def get_history(self, codigo: str, limit: int = 10) -> list[dict]:
        """Devuelve el historial de estados de un expediente."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM expediente_states "
                "WHERE codigo = ? ORDER BY checked_at DESC LIMIT ?",
                (codigo, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_expedientes(self) -> list[str]:
        """Lista todos los expedientes que tienen al menos un estado guardado."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT codigo FROM expediente_states"
            ).fetchall()
        return [r[0] for r in rows]
