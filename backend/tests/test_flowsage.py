import json, sys, os, unittest, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flowsage import auth, tools, reports
from flowsage.db import Database
from flowsage.decider import (SimulatedDecider, StrandsDeciderClient, DeciderError, InvalidDecision,
                              validate_selection, build_state, Decision)
from flowsage.explain import (BedrockExplainer, TemplateExplainer, ExplainError, validate_explanation)
from flowsage.orchestrator import create_incident, investigate, approve_and_execute
from flowsage.scenarios import SCENARIOS, list_scenarios, build_incident


class FakeResp:
    def __init__(self, data): self.data = data
    def read(self): return json.dumps(self.data).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_opener(payload=None, exc=None):
    def opener(req, timeout=None):
        if exc: raise exc
        return FakeResp(payload)
    return opener


class FakeBedrock:
    def __init__(self, text=None, exc=None): self.text, self.exc = text, exc
    def converse(self, **kw):
        if self.exc: raise self.exc
        return {"output": {"message": {"content": [{"text": self.text}]}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.uid = self.db.create_user("a@example.com", "x")


class TestScenarios(Base):
    def test_all_scenarios_deterministic_and_simulated(self):
        for k in list_scenarios():
            a, b = build_incident(k, "X1"), build_incident(k, "X1")
            self.assertEqual(a, b); self.assertTrue(a["simulated"])

    def test_expected_decision_for_each_failing_scenario(self):
        d = SimulatedDecider()
        for k, s in SCENARIOS.items():
            if s["expected_action"] is None: continue
            inc = build_incident(k, "X1")
            dec = d.decide("q", {a: "" for a in tools.ALLOWED_ACTIONS}, build_state(inc, inc["logs"]))
            self.assertEqual(dec.selected, s["expected_action"], k)

    def test_success_scenario_skips_investigation(self):
        inc = create_incident(self.db, self.uid, "success")
        inv = investigate(self.db, self.uid, inc["incident_id"], SimulatedDecider(), TemplateExplainer())
        self.assertIsNone(inv["decision"]); self.assertEqual(self.db.get_incident(self.uid, inc["incident_id"])["status"], "healthy")

    def test_payment_timeout_checks_status_and_does_not_retry(self):
        inc = create_incident(self.db, self.uid, "payment_timeout")
        inv = investigate(self.db, self.uid, inc["incident_id"], SimulatedDecider(), TemplateExplainer())
        self.assertEqual(inv["tool"]["name"], "inspect_payment_status")
        self.assertEqual(inv["recovery"]["key"], "escalate_to_human")      # never blind retry


class TestDeciderPattern(Base):
    OPTS = list(tools.ALLOWED_ACTIONS)

    def test_disallowed_action_rejected(self):
        with self.assertRaises(InvalidDecision): validate_selection("delete_all_orders", self.OPTS)
        with self.assertRaises(InvalidDecision): validate_selection(None, self.OPTS)

    def test_tool_registry_refuses_non_allowlisted(self):
        with self.assertRaises(tools.ToolError): tools.run_tool("rm_rf", build_incident("payment_timeout", "I1"))

    def test_live_client_parses_confidence_and_validates(self):
        payload = {"answers": {"next_action": {"type": "choice", "choice": "inspect_payment_status",
                   "confidence": 0.81, "probabilities": {"inspect_payment_status": 0.9, "inspect_recent_logs": 0.1}}},
                   "latency_ms": 55.0}
        c = StrandsDeciderClient("http://x", opener=fake_opener(payload))
        d = c.decide("q", {a: "" for a in self.OPTS}, "s")
        self.assertTrue(d.is_real_decider); self.assertEqual(d.confidence, 0.81); self.assertEqual(d.latency_ms, 55.0)

    def test_live_client_no_confidence_means_none(self):
        payload = {"answers": {"next_action": {"choice": "inspect_recent_logs"}}}
        d = StrandsDeciderClient("http://x", opener=fake_opener(payload)).decide("q", {a: "" for a in self.OPTS}, "s")
        self.assertIsNone(d.confidence)

    def test_live_client_rejects_out_of_list_answer(self):
        payload = {"answers": {"next_action": {"choice": "wire_money"}}}
        with self.assertRaises(InvalidDecision):
            StrandsDeciderClient("http://x", opener=fake_opener(payload)).decide("q", {a: "" for a in self.OPTS}, "s")

    def test_live_client_unavailable_raises_decider_error(self):
        c = StrandsDeciderClient("http://x", opener=fake_opener(exc=urllib.error.URLError("refused")))
        with self.assertRaises(DeciderError): c.decide("q", {a: "" for a in self.OPTS}, "s")

    def test_decider_failure_fails_closed_no_tool_run(self):
        class Down:
            name = "strands-decider-2b"
            def decide(self, *a): raise DeciderError("decider unavailable")
        inc = create_incident(self.db, self.uid, "payment_timeout")
        inv = investigate(self.db, self.uid, inc["incident_id"], Down(), TemplateExplainer())
        self.assertIsNone(inv["tool"]); self.assertIsNone(inv["recovery"]); self.assertTrue(inv["errors"])
        self.assertEqual(self.db.get_incident(self.uid, inc["incident_id"])["status"], "needs_attention")

    def test_prompt_injection_in_logs_cannot_trigger_tool(self):
        inc = build_incident("scheduled_failure", "I1")
        self.assertTrue(any("IGNORE ALL PREVIOUS" in l for l in inc["logs"]))
        class Inj:
            name = "inj"
            def decide(self, q, c, s):
                return Decision(q, list(c), validate_selection("delete_all_orders", list(c)), "x", False, None)
        c = create_incident(self.db, self.uid, "scheduled_failure")
        inv = investigate(self.db, self.uid, c["incident_id"], Inj(), TemplateExplainer())
        self.assertIsNone(inv["tool"])                      # fail closed: nothing executed
        self.assertTrue(inv["errors"])
        self.assertEqual(self.db.get_incident(self.uid, c["incident_id"])["status"], "needs_attention")

    def test_state_marks_logs_untrusted_and_bounded(self):
        s = build_state(build_incident("scheduled_failure", "I1"), ["x" * 5000] * 50)
        self.assertIn("untrusted", s); self.assertLessEqual(len(s), 2000)


class TestTools(Base):
    def test_argument_validation(self):
        inc = build_incident("payment_timeout", "I1")
        with self.assertRaises(tools.ToolError): tools.inspect_payment_status(inc, {"incident_id": "a; rm -rf /"})
        with self.assertRaises(tools.ToolError): tools.inspect_dependency_health(inc, {"service_name": "../etc"})
        with self.assertRaises(tools.ToolError): tools.inspect_configuration_status(inc, {"component": 5})

    def test_high_risk_recovery_requires_approval(self):
        inc = build_incident("invalid_configuration", "I1")
        with self.assertRaises(tools.ToolError): tools.simulate_safe_recovery(inc, "fix_configuration_value", False)
        self.assertTrue(tools.simulate_safe_recovery(inc, "fix_configuration_value", True)["simulated"])

    def test_unknown_recovery_rejected(self):
        with self.assertRaises(tools.ToolError): tools.simulate_safe_recovery({}, "drop_database", True)


GOOD = {"summary": "s", "evidence": ["payment_status=UNKNOWN", "made up line"], "likely_cause": "c",
        "uncertainty": "u", "recommended_next_step": "n", "safety_considerations": "x", "recovery_explanation": "r"}


class TestBedrock(Base):
    def run_inv(self, client):
        inc = create_incident(self.db, self.uid, "payment_timeout")
        ex = BedrockExplainer("test-model", "us-east-1", client=client)
        return investigate(self.db, self.uid, inc["incident_id"], SimulatedDecider(), ex), inc

    def test_valid_response_grounded_and_ungrounded_dropped(self):
        inv, _ = self.run_inv(FakeBedrock("Here: " + json.dumps(GOOD)))
        e = inv["explanation"]
        self.assertEqual(e["source"], "amazon-bedrock"); self.assertEqual(e["dropped_ungrounded_evidence"], 1)
        self.assertEqual(e["evidence"], ["payment_status=UNKNOWN"])

    def test_malformed_response_recorded_not_fabricated(self):
        inv, inc = self.run_inv(FakeBedrock("not json at all"))
        self.assertIsNone(inv["explanation"]); self.assertEqual(inv["errors"][0]["stage"], "explanation")
        self.assertIn("explanation_failed", [e["kind"] for e in self.db.audit_events(self.uid, inc["incident_id"])])

    def test_bedrock_failure_recorded(self):
        inv, _ = self.run_inv(FakeBedrock(exc=RuntimeError("AccessDenied")))
        self.assertIsNone(inv["explanation"]); self.assertTrue(inv["errors"])

    def test_fully_ungrounded_evidence_rejected(self):
        bad = dict(GOOD, evidence=["invented log"])
        with self.assertRaises(ExplainError): validate_explanation(bad, "real log")

    def test_missing_field_rejected(self):
        bad = {k: v for k, v in GOOD.items() if k != "summary"}
        with self.assertRaises(ExplainError): validate_explanation(bad, "payment_status=UNKNOWN")

    def test_missing_model_id_is_config_error(self):
        with self.assertRaises(ExplainError): BedrockExplainer("", "us-east-1")


class TestAuth(Base):
    def test_hash_roundtrip_and_salting(self):
        h1, h2 = auth.hash_password("correct horse battery"), auth.hash_password("correct horse battery")
        self.assertNotEqual(h1, h2); self.assertTrue(auth.verify_password("correct horse battery", h1))
        self.assertFalse(auth.verify_password("wrong password!!", h1)); self.assertNotIn("correct", h1)

    def test_validation(self):
        with self.assertRaises(auth.AuthError): auth.validate_credentials("not-an-email", "longenoughpw1")
        with self.assertRaises(auth.AuthError): auth.validate_credentials("a@b.co", "short")

    def test_token_valid_tampered_expired(self):
        sec = "s" * 32
        t = auth.make_token(sec, "u1", 60, now=1000)
        self.assertEqual(auth.read_token(sec, t, now=1010), "u1")
        with self.assertRaises(auth.AuthError): auth.read_token(sec, t, now=2000)
        with self.assertRaises(auth.AuthError): auth.read_token(sec, t[:-2] + "xx", now=1010)
        with self.assertRaises(auth.AuthError): auth.read_token("o" * 32, t, now=1010)

    def test_no_secret_no_token(self):
        with self.assertRaises(auth.AuthError): auth.make_token("", "u", 60)

    def test_rate_limiter(self):
        r = auth.RateLimiter(3, 60)
        self.assertEqual([r.allow("k", now=i) for i in range(1, 5)], [True, True, True, False])
        self.assertTrue(r.allow("k", now=100))


class TestIsolationAudit(Base):
    def test_user_isolation(self):
        other = self.db.create_user("b@example.com", "x")
        inc = create_incident(self.db, self.uid, "payment_timeout")
        self.assertIsNone(self.db.get_incident(other, inc["incident_id"]))
        self.assertEqual(self.db.list_incidents(other), [])
        with self.assertRaises(KeyError): investigate(self.db, other, inc["incident_id"], SimulatedDecider(), TemplateExplainer())
        with self.assertRaises(KeyError): reports.incident_report(self.db, other, inc["incident_id"])
        self.assertEqual(self.db.audit_events(other, inc["incident_id"]), [])
        self.assertEqual(reports.dashboard(self.db, other)["total_incidents"], 0)

    def test_sql_injection_string_is_inert(self):
        self.assertIsNone(self.db.user_by_email("x' OR '1'='1"))
        self.assertEqual(self.db.list_incidents(self.uid, scenario="' OR 1=1 --"), [])

    def test_audit_trail_and_approval_flow(self):
        inc = create_incident(self.db, self.uid, "invalid_configuration"); i = inc["incident_id"]
        investigate(self.db, self.uid, i, SimulatedDecider(), TemplateExplainer())
        self.assertEqual(self.db.get_incident(self.uid, i)["status"], "awaiting_approval")
        approve_and_execute(self.db, self.uid, i, True)
        row = self.db.get_incident(self.uid, i)
        self.assertEqual(row["status"], "resolved_simulated")
        kinds = [e["kind"] for e in self.db.audit_events(self.uid, i)]
        for k in ("incident_created", "decision_requested", "decision_returned", "tool_executed",
                  "investigation_completed", "approval_recorded", "recovery_executed"):
            self.assertIn(k, kinds)

    def test_rejection_does_not_execute(self):
        inc = create_incident(self.db, self.uid, "invalid_configuration"); i = inc["incident_id"]
        investigate(self.db, self.uid, i, SimulatedDecider(), TemplateExplainer())
        approve_and_execute(self.db, self.uid, i, False)
        kinds = [e["kind"] for e in self.db.audit_events(self.uid, i)]
        self.assertNotIn("recovery_executed", kinds); self.assertEqual(self.db.get_incident(self.uid, i)["status"], "needs_attention")

    def test_cannot_approve_without_investigation_or_twice(self):
        inc = create_incident(self.db, self.uid, "payment_timeout"); i = inc["incident_id"]
        with self.assertRaises(tools.ToolError): approve_and_execute(self.db, self.uid, i, True)
        investigate(self.db, self.uid, i, SimulatedDecider(), TemplateExplainer())
        approve_and_execute(self.db, self.uid, i, True)
        with self.assertRaises(tools.ToolError): approve_and_execute(self.db, self.uid, i, True)


class TestReports(Base):
    def test_dashboard_from_real_records_and_empty_state(self):
        self.assertEqual(reports.dashboard(self.db, self.uid)["total_incidents"], 0)
        self.assertIsNone(reports.dashboard(self.db, self.uid)["avg_investigation_seconds"])
        for k in list_scenarios():
            c = create_incident(self.db, self.uid, k)
            investigate(self.db, self.uid, c["incident_id"], SimulatedDecider(), TemplateExplainer())
        d = reports.dashboard(self.db, self.uid)
        self.assertEqual(d["total_incidents"], 6); self.assertEqual(d["healthy_runs"], 1)
        self.assertEqual(d["decisions_total"], 5); self.assertEqual(d["decisions_matching_expected"], 5)
        self.assertEqual(d["decisions_from_real_decider"], 0)      # simulated backend is never counted as real

    def test_csv_export_and_formula_guard(self):
        c = create_incident(self.db, self.uid, "payment_timeout")
        investigate(self.db, self.uid, c["incident_id"], SimulatedDecider(), TemplateExplainer())
        out = reports.incidents_csv(self.db, self.uid)
        self.assertIn(c["incident_id"], out); self.assertIn("inspect_payment_status", out)
        self.assertEqual(reports._safe_cell("=1+1"), "'=1+1")

    def test_incident_report_has_required_fields(self):
        c = create_incident(self.db, self.uid, "payment_timeout")
        investigate(self.db, self.uid, c["incident_id"], SimulatedDecider(), TemplateExplainer())
        r = json.loads(reports.incident_json(self.db, self.uid, c["incident_id"]))
        for k in ("incident_id", "selected_action", "evidence", "explanation", "recovery", "audit", "created_at"):
            self.assertIn(k, r)
        self.assertIsNone(r["decider_confidence"])                  # simulated backend: no fake confidence




from flowsage.service import Service, ServiceError
from flowsage.config import Settings


def mk_service(**kw):
    return Service(Settings(secret_key="k" * 32, **kw), db=Database(":memory:"))


class TestService(unittest.TestCase):
    def test_register_login_and_generic_errors(self):
        s = mk_service()
        t = s.register("U@Example.com", "a-long-password")["token"]
        self.assertTrue(s.user_id(t))
        s.login("u@example.com", "a-long-password")
        with self.assertRaises(ServiceError) as a: s.login("u@example.com", "wrong-password!!")
        with self.assertRaises(ServiceError) as b: s.login("nobody@example.com", "wrong-password!!")
        self.assertEqual((a.exception.status, a.exception.msg), (b.exception.status, b.exception.msg))
        with self.assertRaises(ServiceError) as d: s.register("u@example.com", "another-long-pw")
        self.assertEqual(d.exception.status, 409)

    def test_unauthenticated_and_forged_tokens_rejected(self):
        s = mk_service()
        for tok in ("", "garbage", "a.b"):
            with self.assertRaises(ServiceError) as e: s.user_id(tok)
            self.assertEqual(e.exception.status, 401)

    def test_login_rate_limited(self):
        s = mk_service()
        codes = []
        for _ in range(12):
            try: s.login("x@example.com", "whatever-password")
            except ServiceError as e: codes.append(e.status)
        self.assertEqual(codes[:10], [401] * 10); self.assertEqual(codes[10:], [429, 429])

    def test_cross_user_access_blocked_in_service(self):
        s = mk_service()
        a = s.user_id(s.register("a@example.com", "a-long-password", ip="1")["token"])
        b = s.user_id(s.register("b@example.com", "a-long-password", ip="2")["token"])
        inc = s.new_incident(a, "payment_timeout")["incident_id"]
        for fn in (lambda: s.incident(b, inc), lambda: s.run(b, inc), lambda: s.approve(b, inc, True)):
            with self.assertRaises(ServiceError) as e: fn()
            self.assertEqual(e.exception.status, 404)

    def test_unknown_scenario_and_status_has_no_secrets(self):
        s = mk_service()
        with self.assertRaises(ServiceError): s.new_incident("u", "drop_table")
        self.assertNotIn("kkkk", json.dumps(s.status()))
        self.assertFalse(s.status()["decider"]["is_real"])

    def test_bedrock_live_without_model_is_reported_not_faked(self):
        s = mk_service(bedrock_mode="live", bedrock_model_id="")
        self.assertFalse(s.status()["bedrock"]["usable"])
        uid = s.user_id(s.register("c@example.com", "a-long-password")["token"])
        inc = s.new_incident(uid, "payment_timeout")["incident_id"]
        with self.assertRaises(ServiceError) as e: s.run(uid, inc)
        self.assertEqual(e.exception.status, 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)
