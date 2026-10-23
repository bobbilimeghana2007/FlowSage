"""FastAPI HTTP layer (thin). NOTE: not executed in the authoring sandbox (no network to install FastAPI)."""
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from . import reports
from .config import Settings
from .service import Service, ServiceError

settings = Settings.from_env()
svc = Service(settings)
app = FastAPI(title="FlowSage AI", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["authorization", "content-type"])


@app.exception_handler(ServiceError)
async def _svc_err(_, e: ServiceError):
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": e.msg}, status_code=e.status)


def current_user(authorization: str = Header(default="")) -> str:
    return svc.user_id(authorization.removeprefix("Bearer ").strip())


class Creds(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=128)


class NewIncident(BaseModel):
    scenario: str = Field(max_length=40)


class Approval(BaseModel):
    approved: bool


@app.post("/api/auth/register")
def register(c: Creds, r: Request): return svc.register(c.email, c.password, r.client.host if r.client else "-")
@app.post("/api/auth/login")
def login(c: Creds, r: Request): return svc.login(c.email, c.password, r.client.host if r.client else "-")
@app.get("/api/status")
def status(_: str = Depends(current_user)): return svc.status()
@app.get("/api/dashboard")
def dashboard(uid: str = Depends(current_user)): return reports.dashboard(svc.db, uid)
@app.get("/api/incidents")
def incidents(scenario: str = None, status: str = None, uid: str = Depends(current_user)):
    return svc.db.list_incidents(uid, scenario, status)
@app.post("/api/incidents")
def new_incident(b: NewIncident, uid: str = Depends(current_user)): return svc.new_incident(uid, b.scenario)
@app.get("/api/incidents/{iid}")
def get_incident(iid: str, uid: str = Depends(current_user)): return svc.incident(uid, iid)
@app.post("/api/incidents/{iid}/investigate")
def investigate(iid: str, uid: str = Depends(current_user)): return svc.run(uid, iid)
@app.post("/api/incidents/{iid}/approval")
def approval(iid: str, b: Approval, uid: str = Depends(current_user)): return svc.approve(uid, iid, b.approved)
@app.get("/api/incidents/{iid}/audit")
def audit(iid: str, uid: str = Depends(current_user)): svc.incident(uid, iid); return svc.db.audit_events(uid, iid)
@app.get("/api/incidents/{iid}/report.json")
def report_json(iid: str, uid: str = Depends(current_user)):
    try: return PlainTextResponse(reports.incident_json(svc.db, uid, iid), media_type="application/json")
    except KeyError: raise HTTPException(404, "incident not found")
@app.get("/api/reports/incidents.csv")
def csv_export(uid: str = Depends(current_user)):
    return PlainTextResponse(reports.incidents_csv(svc.db, uid), media_type="text/csv",
                             headers={"content-disposition": "attachment; filename=flowsage_incidents.csv"})
