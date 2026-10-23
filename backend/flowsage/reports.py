"""Analytics and exports computed from stored records only (no hardcoded numbers)."""
import csv
import io
import json
from collections import Counter

from .db import Database


def _safe_cell(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s     # CSV formula-injection guard


def dashboard(db: Database, user_id: str) -> dict:
    rows = db.list_incidents(user_id)
    durations = [r["investigation"]["duration_s"] for r in rows
                 if r["investigation"] and r["investigation"].get("duration_s") is not None
                 and r["status"] != "healthy"]
    decided = [r for r in rows if r["investigation"] and r["investigation"].get("decision")]
    correct = sum(1 for r in decided if r["investigation"]["decision"].get("correct_vs_expected"))
    real = sum(1 for r in decided if r["investigation"]["decision"].get("is_real_decider"))
    return {
        "total_incidents": len(rows),
        "resolved_simulations": sum(1 for r in rows if r["status"] == "resolved_simulated"),
        "needs_attention": sum(1 for r in rows if r["status"] in ("awaiting_approval", "needs_attention")),
        "healthy_runs": sum(1 for r in rows if r["status"] == "healthy"),
        "avg_investigation_seconds": (sum(durations) / len(durations)) if durations else None,
        "by_scenario": dict(Counter(r["scenario"] for r in rows)),
        "by_status": dict(Counter(r["status"] for r in rows)),
        "decisions_total": len(decided),
        "decisions_matching_expected": correct,
        "decisions_from_real_decider": real,
        "error_count": sum(len(r["investigation"]["errors"]) for r in rows if r["investigation"]),
        "recent": [{"id": r["id"], "scenario": r["scenario"], "status": r["status"],
                    "created_at": r["created_at"]} for r in rows[:5]],
    }


def incident_report(db: Database, user_id: str, incident_id: str) -> dict:
    row = db.get_incident(user_id, incident_id)
    if row is None:
        raise KeyError("incident not found")
    inv = row["investigation"] or {}
    return {"incident_id": incident_id, "simulated": True, "scenario": row["scenario"],
            "status": row["status"], "created_at": row["created_at"],
            "selected_action": (inv.get("decision") or {}).get("selected"),
            "decision_backend": (inv.get("decision") or {}).get("backend"),
            "decider_confidence": (inv.get("decision") or {}).get("confidence"),
            "evidence": row["incident"]["logs"], "tool": inv.get("tool"),
            "explanation": inv.get("explanation"), "recovery": inv.get("recovery"),
            "errors": inv.get("errors", []), "audit": db.audit_events(user_id, incident_id)}


def incidents_csv(db: Database, user_id: str, scenario=None, status=None) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["incident_id", "timestamp", "scenario", "status", "selected_action", "decision_backend",
                "decider_confidence", "approval_outcome", "explanation_source", "simulated"])
    for r in db.list_incidents(user_id, scenario, status):
        inv = r["investigation"] or {}
        d, rec = inv.get("decision") or {}, inv.get("recovery") or {}
        w.writerow([_safe_cell(x) for x in [r["id"], r["created_at"], r["scenario"], r["status"],
                    d.get("selected"), d.get("backend"), d.get("confidence"), rec.get("status"),
                    (inv.get("explanation") or {}).get("source"), True]])
    return out.getvalue()


def incident_json(db, user_id, incident_id) -> str:
    return json.dumps(incident_report(db, user_id, incident_id), indent=2, default=str)
