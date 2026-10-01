import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description  TEXT,
    priority     TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    due_date     TEXT,
    done         INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    created_at   TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);
"""


def connect(path: str) -> sqlite3.Connection:
    # Uma conexão por requisição. O FastAPI pode abrir e usar a conexão em threads diferentes
    # do pool, mas nunca ao mesmo tempo, então desligar a checagem de thread é seguro aqui.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
