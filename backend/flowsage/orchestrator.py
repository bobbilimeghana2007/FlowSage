"""Investigation pipeline. Model proposes; the app enforces allowlist, bounds, approval."""
import time
import uuid
from typing import Optional

from . import tools
from .db import Database
from .decider import DeciderError, build_state
from .explain import ExplainError
from .scenarios import SCENARIOS, build_incident

MAX_STEPS = 3     # hard bound on agent steps; the current design uses one decision + one tool


def recovery_policy(scenario: str, action: str, result: dict) -> dict:
    """App-defined policy (NOT model output). Maps verified tool evidence to a recovery."""
    if action == "inspect_payment_status":
        if result.get("payment_status") == "unknown_after_timeout":
            return {"key": "escalate_to_human", "label": "Do NOT retry yet; escalate for manual payment check",
                    "why": "Payment state is unknown after a timeout; a retry risks duplicate processing.",
                    "high_risk": False}
        return {"key": "retry_workflow_step", "label": "Retry the failed step", "why": "Payment confirmed captured.", "high_risk": False}
    if action == "inspect_dependency_health":
        if result.get("status") in ("down", "unknown_service"):
            return {"key": "escalate_to_human", "label": "Escalate: dependency is down", "why": "Retrying a down service will keep failing.", "high_risk": False}
        return {"key": "retry_workflow_step", "label": "Retry the step", "why": "Dependency not down.", "high_risk": False}
    if action == "inspect_configuration_status":
        if result.get("config", {}).get("valid") is False:
            return {"key": "fix_configuration_value", "label": "Apply corrected configuration (needs approval)",
                    "why": "Configuration is invalid; retries cannot succeed until it is fixed.", "high_risk": True}
        return {"key": "retry_workflow_step", "label": "Retry the step", "why": "Configuration valid.", "high_risk": False}
    if action == "inspect_recent_logs":
        if scenario == "api_rate_limit":
            return {"key": "wait_and_retry_after_backoff", "label": "Wait for the rate-limit window, then retry",
                    "why": "Logs show repeated HTTP 429 with a retry-after hint.", "high_risk": False}
        return {"key": "retry_workflow_step", "label": "Retry the scheduled job", "why": "Logs show a missed schedule window.", "high_risk": False}
    return {"key": "escalate_to_human", "label": "Escalate to a human", "why": "Evidence insufficient for automated recovery.", "high_risk": False}


def create_incident(db: Database, user_id: str, scenario: str) -> dict:
    inc = build_incident(scenario, "INC-" + uuid.uuid4().hex[:10])
    db.add_incident(user_id, inc)
    db.audit(user_id, inc["incident_id"], "incident_created", {"scenario": scenario, "simulated": True})
    return inc


def investigate(db: Database, user_id: str, incident_id: str, decider, explainer) -> dict:
    row = db.get_incident(user_id, incident_id)
    if row is None:
        raise KeyError("incident not found")
    inc, scen = row["incident"], SCENARIOS[row["scenario"]]
    t_start = time.time()
    timeline = [{"step": "incident_received", "ts": t_start, "ok": True}]
    aud = lambda k, d: db.audit(user_id, incident_id, k, d)
    inv = {"started_at": t_start, "timeline": timeline, "decision": None, "tool": None,
           "explanation": None, "recovery": None, "errors": [], "steps_used": 0,
           "expected_action": scen["expected_action"]}

    if not inc["failed"]:
        timeline.append({"step": "no_failure_detected", "ts": time.time(), "ok": True})
        inv.update(finished_at=time.time(), duration_s=time.time() - t_start)
        aud("investigation_skipped", {"reason": "workflow healthy"})
        db.update_incident(user_id, incident_id, "healthy", inv)
        return inv

    evidence = list(inc["logs"])
    timeline.append({"step": "evidence_collected", "ts": time.time(), "ok": True, "count": len(evidence)})
    question = "Which single diagnostic action should run next?"
    criteria = {a: tools.ACTION_DESCRIPTIONS[a] for a in tools.ALLOWED_ACTIONS}
    timeline.append({"step": "options_prepared", "ts": time.time(), "ok": True, "options": list(criteria)})
    aud("decision_requested", {"question": question, "options": list(criteria), "decider": decider.name})

    try:
        dec = decider.decide(question, criteria, build_state(inc, evidence))
        inv["steps_used"] += 1
    except DeciderError as e:
        inv["errors"].append({"stage": "decision", "error": str(e)})
        timeline.append({"step": "decider_invoked", "ts": time.time(), "ok": False, "error": str(e)})
        aud("decision_failed", {"error": str(e)})
        inv.update(finished_at=time.time(), duration_s=time.time() - t_start)
        db.update_incident(user_id, incident_id, "needs_attention", inv)
        return inv          # fail closed: no tool executed, no recovery proposed

    inv["decision"] = dec.to_dict()
    inv["decision"]["correct_vs_expected"] = (dec.selected == scen["expected_action"])
    timeline.append({"step": "decision_returned", "ts": time.time(), "ok": True, "selected": dec.selected,
                     "backend": dec.backend, "is_real_decider": dec.is_real_decider})
    aud("decision_returned", inv["decision"])

    t0 = time.perf_counter()
    try:
        result = tools.run_tool(dec.selected, inc)            # allowlist enforced here as well
        inv["tool"] = {"name": dec.selected, "result": result, "duration_ms": (time.perf_counter() - t0) * 1000}
        timeline.append({"step": "tool_executed", "ts": time.time(), "ok": True, "tool": dec.selected})
        aud("tool_executed", inv["tool"])
    except tools.ToolError as e:
        inv["errors"].append({"stage": "tool", "error": str(e)})
        timeline.append({"step": "tool_executed", "ts": time.time(), "ok": False, "error": str(e)})
        aud("tool_failed", {"error": str(e)})
        inv.update(finished_at=time.time(), duration_s=time.time() - t_start)
        db.update_incident(user_id, incident_id, "needs_attention", inv)
        return inv

    rec = recovery_policy(row["scenario"], dec.selected, result)
    inv["recovery"] = {**rec, "options_available": tools.RECOVERIES, "status": "awaiting_approval"}
    try:
        inv["explanation"] = explainer.explain(inc, dec.to_dict(), dec.selected, result, rec)
        timeline.append({"step": "explanation_generated", "ts": time.time(), "ok": True,
                         "source": inv["explanation"]["source"]})
    except ExplainError as e:
        inv["errors"].append({"stage": "explanation", "error": str(e)})
        timeline.append({"step": "explanation_generated", "ts": time.time(), "ok": False, "error": str(e)})
        aud("explanation_failed", {"error": str(e)})
    timeline.append({"step": "recovery_recommended", "ts": time.time(), "ok": True, "recovery": rec["key"]})
    inv.update(finished_at=time.time(), duration_s=time.time() - t_start)
    db.update_incident(user_id, incident_id, "awaiting_approval", inv)
    aud("investigation_completed", {"duration_s": inv["duration_s"], "errors": inv["errors"]})
    return inv


def approve_and_execute(db: Database, user_id: str, incident_id: str, approved: bool) -> dict:
    row = db.get_incident(user_id, incident_id)
    if row is None:
        raise KeyError("incident not found")
    inv = row["investigation"]
    if not inv or not inv.get("recovery") or row["status"] != "awaiting_approval":
        raise tools.ToolError("no recovery awaiting approval")
    rec = inv["recovery"]
    db.audit(user_id, incident_id, "approval_recorded", {"approved": bool(approved), "recovery": rec["key"]})
    if not approved:
        inv["recovery"]["status"] = "rejected"
        db.update_incident(user_id, incident_id, "needs_attention", inv)
        return inv
    try:
        out = tools.simulate_safe_recovery(row["incident"], rec["key"], approved=True)
    except tools.ToolError as e:
        db.audit(user_id, incident_id, "recovery_failed", {"error": str(e)})
        raise
    inv["recovery"].update(status="executed_simulated", result=out)
    db.audit(user_id, incident_id, "recovery_executed", out)
    db.update_incident(user_id, incident_id, "resolved_simulated", inv)
    return inv
