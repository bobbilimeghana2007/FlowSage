"""Application service: what the HTTP layer calls. Framework-free so it is unit-tested."""
from . import auth, orchestrator, reports, tools
from .config import Settings
from .db import Database
from .decider import make_decider
from .explain import make_explainer, ExplainError
from .scenarios import SCENARIOS


class ServiceError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg); self.status, self.msg = status, msg


class Service:
    def __init__(self, settings: Settings, db: Database = None, decider=None, explainer=None):
        self.s = settings
        self.db = db or Database(settings.db_path)
        self.decider = decider or make_decider(settings.decider_mode, settings.decider_url, settings.decider_timeout_s)
        if explainer is not None:
            self.explainer = explainer
        else:
            try:
                self.explainer = make_explainer(settings.bedrock_mode, settings.bedrock_model_id,
                                                settings.aws_region, settings.bedrock_timeout_s)
            except ExplainError:
                self.explainer = None            # configuration error surfaced in /settings
        self.login_limiter = auth.RateLimiter(10, 300)
        self.api_limiter = auth.RateLimiter(120, 60)

    # --- auth
    def register(self, email, password, ip="-"):
        if not self.login_limiter.allow("reg:" + ip): raise ServiceError(429, "too many attempts")
        try: auth.validate_credentials(email, password)
        except auth.AuthError as e: raise ServiceError(422, str(e))
        email = email.strip().lower()
        if self.db.user_by_email(email): raise ServiceError(409, "could not register with these details")
        uid = self.db.create_user(email, auth.hash_password(password))
        return {"token": auth.make_token(self.s.secret_key, uid, self.s.token_ttl_s)}

    def login(self, email, password, ip="-"):
        if not self.login_limiter.allow("login:" + ip): raise ServiceError(429, "too many attempts")
        u = self.db.user_by_email((email or "").strip().lower())
        ok = auth.verify_password(password or "", u["pw_hash"]) if u else auth.verify_password(password or "", auth.hash_password("x"*12))
        if not u or not ok: raise ServiceError(401, "invalid email or password")   # same message for both
        return {"token": auth.make_token(self.s.secret_key, u["id"], self.s.token_ttl_s)}

    def user_id(self, token):
        try: uid = auth.read_token(self.s.secret_key, token or "")
        except auth.AuthError: raise ServiceError(401, "not authenticated")
        if not self.api_limiter.allow(uid): raise ServiceError(429, "rate limit exceeded")
        return uid

    # --- incidents
    def new_incident(self, uid, scenario):
        if scenario not in SCENARIOS: raise ServiceError(422, "unknown scenario")
        return orchestrator.create_incident(self.db, uid, scenario)

    def run(self, uid, incident_id):
        if self.explainer is None: raise ServiceError(503, "Bedrock is selected but BEDROCK_MODEL_ID is not configured")
        try: return orchestrator.investigate(self.db, uid, incident_id, self.decider, self.explainer)
        except KeyError: raise ServiceError(404, "incident not found")

    def approve(self, uid, incident_id, approved):
        try: return orchestrator.approve_and_execute(self.db, uid, incident_id, bool(approved))
        except KeyError: raise ServiceError(404, "incident not found")
        except tools.ToolError as e: raise ServiceError(409, str(e))

    def incident(self, uid, incident_id):
        r = self.db.get_incident(uid, incident_id)
        if not r: raise ServiceError(404, "incident not found")
        return r

    def status(self):
        """Integration health with NO secrets."""
        return {"demo_mode": True,
                "decider": {"mode": self.s.decider_mode, "is_real": self.decider.is_real, "url_configured": bool(self.s.decider_url)},
                "bedrock": {"mode": self.s.bedrock_mode, "model_configured": bool(self.s.bedrock_model_id),
                            "region": self.s.aws_region, "usable": self.explainer is not None},
                "secret_key_configured": len(self.s.secret_key) >= 16}
