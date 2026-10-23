# Evaluation (fill in ONLY with measured values)
Expected action per scenario is defined in `backend/flowsage/scenarios.py` (app-defined, not a benchmark).
| Scenario | Expected action | Decider 2B selected | Confidence | Latency (ms) | Match |
|---|---|---|---|---|---|
| Payment timeout | inspect_payment_status | [measure] | [measure] | [measure] | [ ] |
| Dependency unavailable | inspect_dependency_health | [measure] | [measure] | [measure] | [ ] |
| API rate limit | inspect_recent_logs | [measure] | [measure] | [measure] | [ ] |
| Invalid configuration | inspect_configuration_status | [measure] | [measure] | [measure] | [ ] |
| Scheduled failure | inspect_recent_logs | [measure] | [measure] | [measure] | [ ] |
Genuine screenshots to capture: landing, dashboard (with data), incident + workflow graph, investigation timeline, decision trace (live confidence), root-cause/recovery with approval, reports/CSV, settings health.
