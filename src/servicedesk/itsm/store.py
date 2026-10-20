"""Mock ITSM store (SQLite) with ServiceNow-style incident fields, plus the audit log."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from ..config import RUNTIME_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS incident (
    number TEXT PRIMARY KEY,
    opened_at TEXT, caller_email TEXT, short_description TEXT, description TEXT,
    category TEXT, cmdb_ci TEXT, impact TEXT, urgency TEXT, priority TEXT,
    assignment_group TEXT, state TEXT, resolution_notes TEXT, work_notes TEXT,
    proposed_response TEXT, gate_reasons TEXT, run_id TEXT
);
CREATE TABLE IF NOT EXISTS audit_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, run_id TEXT, ticket TEXT, step TEXT, input_hash TEXT, output TEXT,
    confidence REAL, model TEXT, prompt_version TEXT, latency_ms REAL,
    tokens_in INTEGER, tokens_out INTEGER, reason TEXT
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class Store:
    """Thread-safe SQLite store. One file per run keeps experiments isolated."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or RUNTIME_DIR / "itsm.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ---------------- incidents
    def next_number(self) -> str:
        cur = self.conn.execute("SELECT COUNT(*) FROM incident")
        return f"INC{10001 + cur.fetchone()[0]:07d}"

    def create_incident(self, fields: dict) -> str:
        with self._lock:
            number = fields.get("number") or self.next_number()
            row = {"number": number, "opened_at": now(), "state": "New", **fields}
            cols = ",".join(row)
            self.conn.execute(f"INSERT INTO incident ({cols}) VALUES ({','.join('?' * len(row))})", list(row.values()))
            self.conn.commit()
        return number

    def update_incident(self, number: str, fields: dict) -> None:
        if not fields:
            return
        with self._lock:
            sets = ",".join(f"{k}=?" for k in fields)
            self.conn.execute(f"UPDATE incident SET {sets} WHERE number=?", [*fields.values(), number])
            self.conn.commit()

    def get_incident(self, number: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM incident WHERE number=?", (number,)).fetchone()
        return dict(row) if row else None

    def list_incidents(self, state: str | None = None) -> list[dict]:
        if state:
            rows = self.conn.execute("SELECT * FROM incident WHERE state=? ORDER BY number", (state,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM incident ORDER BY number").fetchall()
        return [dict(r) for r in rows]

    # ---------------- audit
    def audit(self, *, run_id: str, ticket: str | None, step: str, input_text: str = "", output=None,
              confidence: float | None = None, model: str | None = None, prompt_version: str | None = None,
              latency_ms: float | None = None, tokens_in: int | None = None, tokens_out: int | None = None,
              reason: str | None = None) -> None:
        out = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, default=str)
        with self._lock:
            self.conn.execute(
                "INSERT INTO audit_event (ts,run_id,ticket,step,input_hash,output,confidence,model,prompt_version,"
                "latency_ms,tokens_in,tokens_out,reason) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (now(), run_id, ticket, step, sha(input_text) if input_text else None, out, confidence, model,
                 prompt_version, latency_ms, tokens_in, tokens_out, reason))
            self.conn.commit()

    def relabel_pending(self, pending: str, number: str) -> None:
        """Attach audit events written before the ticket number existed (intake) to the ticket."""
        with self._lock:
            self.conn.execute("UPDATE audit_event SET ticket=? WHERE ticket=?", (number, pending))
            self.conn.commit()

    def audit_events(self, ticket: str | None = None) -> list[dict]:
        if ticket:
            rows = self.conn.execute("SELECT * FROM audit_event WHERE ticket=? ORDER BY id", (ticket,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM audit_event ORDER BY id").fetchall()
        return [dict(r) for r in rows]
