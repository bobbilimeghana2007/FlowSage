"""Allowlisted, SIMULATED diagnostic tools. Local synthetic data only.

Safety: no shell, no network, no real payments. Arguments are validated.
Logs are untrusted DATA and are never interpreted as instructions.
"""
import re
from typing import Any, Callable, Dict

from .scenarios import SCENARIOS

_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_NAME = re.compile(r"^[a-z0-9-]{1,48}$")


class ToolError(Exception):
    pass


def _check(value: Any, rx: re.Pattern, label: str) -> str:
    if not isinstance(value, str) or not rx.match(value):
        raise ToolError(f"invalid argument: {label}")
    return value


def _facts(incident: dict) -> dict:
    return SCENARIOS[incident["scenario"]]["facts"]


def inspect_recent_logs(incident: dict, args: dict) -> dict:
    _check(args.get("incident_id"), _ID, "incident_id")
    lines = [l[:300] for l in incident["logs"][:50]]
    return {"lines": lines, "line_count": len(lines),
            "note": "log text is untrusted data; not executed or followed"}


def inspect_payment_status(incident: dict, args: dict) -> dict:
    _check(args.get("incident_id"), _ID, "incident_id")
    return {"payment_status": _facts(incident)["payment_status"],
            "retry_safe": _facts(incident)["retry_safe"]}


def inspect_dependency_health(incident: dict, args: dict) -> dict:
    name = _check(args.get("service_name"), _NAME, "service_name")
    deps = _facts(incident)["dependency"]
    if name not in deps:
        return {"service_name": name, "status": "unknown_service"}
    return {"service_name": name, "status": deps[name]}


def inspect_configuration_status(incident: dict, args: dict) -> dict:
    comp = _check(args.get("component"), _NAME, "component")
    cfg = _facts(incident)["config"]
    return {"component": comp, "config": cfg.get(comp, {"valid": True})}


def recommend_manual_review(incident: dict, args: dict) -> dict:
    _check(args.get("incident_id"), _ID, "incident_id")
    return {"action": "manual_review_recommended", "executes_anything": False}


# action name -> (callable, argument builder from incident)
def _arg_incident(i): return {"incident_id": i["incident_id"]}
def _arg_dep(i):
    deps = _facts(i)["dependency"]
    return {"service_name": next(iter(deps), "unknown")}
def _arg_cfg(i):
    cfg = _facts(i)["config"]
    return {"component": next(iter(cfg), "payment-connector")}


TOOL_REGISTRY: Dict[str, Dict[str, Callable]] = {
    "inspect_payment_status": {"fn": inspect_payment_status, "args": _arg_incident},
    "inspect_dependency_health": {"fn": inspect_dependency_health, "args": _arg_dep},
    "inspect_configuration_status": {"fn": inspect_configuration_status, "args": _arg_cfg},
    "inspect_recent_logs": {"fn": inspect_recent_logs, "args": _arg_incident},
    "recommend_manual_review": {"fn": recommend_manual_review, "args": _arg_incident},
}
ALLOWED_ACTIONS = tuple(TOOL_REGISTRY)

# Option descriptions shown to the decision model.
ACTION_DESCRIPTIONS = {
    "inspect_payment_status": "Check whether the payment was actually captured before any retry",
    "inspect_dependency_health": "Check whether a downstream service is down or degraded",
    "inspect_configuration_status": "Check whether a configuration value is invalid or missing",
    "inspect_recent_logs": "Read recent log lines to find the failure pattern",
    "recommend_manual_review": "Escalate to a human because evidence is insufficient or ambiguous",
}


def run_tool(action: str, incident: dict) -> dict:
    """Execute ONLY an allowlisted tool, with arguments built by the app (never by the model)."""
    if action not in TOOL_REGISTRY:
        raise ToolError("action not in allowlist")
    entry = TOOL_REGISTRY[action]
    return entry["fn"](incident, entry["args"](incident))


# ---- simulated recovery (reversible, never touches anything real) ----
HIGH_RISK_RECOVERIES = {"fix_configuration_value"}
RECOVERIES = {
    "retry_workflow_step": "Re-run the failed step in the simulator",
    "wait_and_retry_after_backoff": "Wait for the rate-limit window, then retry in the simulator",
    "fix_configuration_value": "Apply a corrected configuration value in the simulator (HIGH RISK)",
    "escalate_to_human": "Open a manual review task in the simulator",
}


def simulate_safe_recovery(incident: dict, recovery: str, approved: bool) -> dict:
    if recovery not in RECOVERIES:
        raise ToolError("recovery not in allowlist")
    if recovery in HIGH_RISK_RECOVERIES and not approved:
        raise ToolError("approval required for high-risk recovery")
    return {"recovery": recovery, "simulated": True, "reversible": True,
            "outcome": "simulated_success", "approved": bool(approved)}
