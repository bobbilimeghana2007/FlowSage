"""SQLite storage. Parameterised queries only; every read is scoped by user_id."""
import json
import sqlite3
import threading
import time
import uuid
from typing import Any, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS incidents(
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, scenario TEXT NOT NULL, status TEXT NOT NULL,
  incident_json TEXT NOT NULL, investigation_json TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_inc_user ON incidents(user_id, created_at);
CREATE TABLE IF NOT EXISTS audit_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL, user_id TEXT NOT NULL,
  ts REAL NOT NULL, kind TEXT NOT NULL, detail_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_audit_inc ON audit_events(incident_id, user_id);
"""


class Database:
    def __init__(self, path: str = ":memory:"):
        self._lock = threading.RLock()
        self._c = sqlite3.connect(path, check_same_thread=False)
        self._c.row_factory = sqlite3.Row
        with self._lock:
            self._c.executescript(SCHEMA)
            self._c.commit()

    def _run(self, sql: str, params: tuple = (), many: bool = True):
        with self._lock:
            cur = self._c.execute(sql, params)
            self._c.commit()
            return cur.fetchall() if many else cur

    # users
    def create_user(self, email: str, pw_hash: str) -> str:
        uid = uuid.uuid4().hex
        self._run("INSERT INTO users VALUES(?,?,?,?)", (uid, email, pw_hash, time.time()))
        return uid

    def user_by_email(self, email: str):
        r = self._run("SELECT * FROM users WHERE email=?", (email,))
        return dict(r[0]) if r else None

    # incidents
    def add_incident(self, user_id: str, incident: dict) -> None:
        now = time.time()
        self._run("INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?)",
                  (incident["incident_id"], user_id, incident["scenario"], "open",
                   json.dumps(incident), None, now, now))

    def get_incident(self, user_id: str, incident_id: str) -> Optional[dict]:
        r = self._run("SELECT * FROM incidents WHERE id=? AND user_id=?", (incident_id, user_id))
        return self._inc(r[0]) if r else None

    def list_incidents(self, user_id: str, scenario: Optional[str] = None,
                       status: Optional[str] = None) -> List[dict]:
        sql, p = "SELECT * FROM incidents WHERE user_id=?", [user_id]
        if scenario:
            sql += " AND scenario=?"; p.append(scenario)
        if status:
            sql += " AND status=?"; p.append(status)
        return [self._inc(r) for r in self._run(sql + " ORDER BY created_at DESC", tuple(p))]

    def update_incident(self, user_id: str, incident_id: str, status: str,
                        investigation: Optional[dict]) -> None:
        self._run("UPDATE incidents SET status=?, investigation_json=?, updated_at=? WHERE id=? AND user_id=?",
                  (status, json.dumps(investigation) if investigation is not None else None,
                   time.time(), incident_id, user_id))

    @staticmethod
    def _inc(r) -> dict:
        d = dict(r)
        d["incident"] = json.loads(d.pop("incident_json"))
        inv = d.pop("investigation_json")
        d["investigation"] = json.loads(inv) if inv else None
        return d

    # audit
    def audit(self, user_id: str, incident_id: str, kind: str, detail: Any) -> None:
        self._run("INSERT INTO audit_events(incident_id,user_id,ts,kind,detail_json) VALUES(?,?,?,?,?)",
                  (incident_id, user_id, time.time(), kind, json.dumps(detail)))

    def audit_events(self, user_id: str, incident_id: str) -> List[dict]:
        rows = self._run("SELECT ts,kind,detail_json FROM audit_events WHERE incident_id=? AND user_id=? ORDER BY id",
                         (incident_id, user_id))
        return [{"ts": r["ts"], "kind": r["kind"], "detail": json.loads(r["detail_json"])} for r in rows]
