# Reusable pattern: "Constrained next-action decision" with Strands Decider 2B

**Question (typed):** `Which single diagnostic action should run next?`
**Options (constrained):** keys of `tools.ACTION_DESCRIPTIONS` → `inspect_payment_status`, `inspect_dependency_health`,
`inspect_configuration_status`, `inspect_recent_logs`, `recommend_manual_review`. Each has a one-line criterion.
**State:** `decider.build_state()` – incident summary + log lines framed as untrusted data, truncated to 2000 chars.

## Steps (all in `backend/flowsage/decider.py` + `orchestrator.py`)
1. Build `criteria = {action: description}` from the allowlist.
2. `StrandsDeciderClient.decide()` sends `POST /v1/systemone` with one `choice` question (format from the official README).
3. `validate_selection()` rejects anything not in the option list (`InvalidDecision`).
4. The orchestrator maps `selected` → `tools.TOOL_REGISTRY[selected]`; **the app builds the arguments**, never the model.
5. Result, decision, confidence (if supplied), latency go to the audit table.
6. Any `DeciderError` → **fail closed**: no tool runs, incident marked `needs_attention`.
7. Agent steps are bounded (`MAX_STEPS`; current design = one decision + one tool).

## Drop-in for another agent
Copy `decider.py`; replace `ACTION_DESCRIPTIONS` and `TOOL_REGISTRY` with your own; call
`decide(question, criteria, state)`; branch on `Decision.selected` and (if present) `Decision.confidence`.
The official docs suggest acting automatically only at high confidence (≥0.9 in their calibration notes) and
confirming with a person below that — a natural next extension is a `confidence < 0.9 → Confirm` branch.

## Strands `InterventionHandler` wiring — SKETCH, UNVERIFIED
The official blog/README describe `InterventionHandler.before_tool_call` returning `Proceed`/`Deny`/`Confirm`/`Guide`
and passing handlers via `Agent(interventions=[...])`. I did not have the SDK installed, so I have **not** verified
exact signatures. Copy the working shape from the official `examples/strands/tool_call_intervention.py` in
`strands-labs/strands-decider`, and put `decide()` + `validate_selection()` inside `before_tool_call`
(return `Proceed` if the proposed tool equals the decided one, else `Guide` with feedback). Mark this section
"verified" in your submission only after you have run it.
