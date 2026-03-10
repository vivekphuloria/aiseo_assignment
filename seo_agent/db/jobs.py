import sqlite3
from typing import Optional
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "jobs.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_jobs_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                thread_id       TEXT PRIMARY KEY,
                status          TEXT NOT NULL,
                execution_stage TEXT,
                topic           TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message   TEXT,
                result_preview  TEXT,
                result_json     TEXT
            )
        """)
        conn.commit()


def create_job(thread_id: str, topic: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO jobs (thread_id, status, topic) VALUES (?, 'pending', ?)",
            (thread_id, topic),
        )
        conn.commit()


def update_job(
    thread_id: str,
    status: Optional[str] = None,
    execution_stage: Optional[str] = None,
    error_message: Optional[str] = None,
    result_preview: Optional[str] = None,
    result_json: Optional[str] = None,
) -> None:
    fields = ["updated_at = CURRENT_TIMESTAMP"]
    params: list = []

    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if execution_stage is not None:
        fields.append("execution_stage = ?")
        params.append(execution_stage)
    if error_message is not None:
        fields.append("error_message = ?")
        params.append(error_message)
    if result_preview is not None:
        fields.append("result_preview = ?")
        params.append(result_preview)
    if result_json is not None:
        fields.append("result_json = ?")
        params.append(result_json)

    params.append(thread_id)
    with _conn() as conn:
        conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE thread_id = ?",
            params,
        )
        conn.commit()


def get_job(thread_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE thread_id = ?", (thread_id,)
        ).fetchone()
    return dict(row) if row else None
