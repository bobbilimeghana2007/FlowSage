# FlowSage AI — Self-Healing Workflow Agent

> Detect the failure. Decide the next step. Explain the evidence. Recover safely.

FlowSage investigates failures in a **simulated** e-commerce order workflow
(Order Received → Payment Verification → Order Confirmation → Dispatch). It collects evidence, asks
**Strands Decider 2B** to choose the next *diagnostic* action from an explicit allowlist, runs only that
allowlisted tool, has **Amazon Bedrock** explain the result from the collected evidence, and asks a human to
approve a *simulated* recovery. It never touches real payments, orders or infrastructure.

Author: Meghana Bobbili — B.Tech AI & Data Science (3rd year, exp. 2028), Ramachandra College of Engineering, Eluru, India.
[GitHub](https://github.com/bobbilimeghana2007) · [LinkedIn](https://linkedin.com/in/bobbili-meghana). License: MIT.

## Honest implementation status

| Area | Status |
|---|---|
| Decision pattern, tools allowlist, scenarios, orchestrator, SQLite audit, auth, Bedrock client, reports | **Implemented and tested** (41 automated tests, run and passing — see `docs/TEST_RESULTS.txt`) |
| FastAPI HTTP layer (`backend/flowsage/api.py`) | Written, compiles. **Not executed yet** (FastAPI could not be installed in the authoring sandbox). Business logic it calls *is* tested. |
| React/Vite/Tailwind frontend | Written; syntax-checked with `tsc` (0 syntax errors). **Never built or run, no screenshots yet.** Run `npm run build` first and fix any type errors. |
| **Real Strands Decider 2B** | Client implemented against the documented `POST /v1/systemone` API. **Not run against a real model** (no network/GPU here). Run `scripts/check_decider.py` once to confirm the `choice` response field names (see below). Until then the app uses the labelled **simulated rules** backend. |
| **Real Amazon Bedrock** | Client implemented (Converse API) and tested with a fake client. **No real AWS call has been made.** |
| Article / video / public URLs | Drafts only. Nothing is published. |

## Run it on Windows 10 (PowerShell)

```powershell
cd flowsage
.\scripts\setup.ps1      # venv, backend deps, npm install; creates .env with demo-safe defaults
.\scripts\test.ps1       # backend tests (standard-library unittest; needs no extra packages)
.\scripts\start.ps1      # API :8000 + UI :5173 -> open http://localhost:5173
```
Direct test command: `cd backend; python -m unittest discover -s tests -v`
Frontend check: `cd frontend; npm install; npm run build` (type-checks, then builds).

Default mode costs nothing: `FLOWSAGE_DECIDER_MODE=simulated`, `FLOWSAGE_BEDROCK_MODE=off`. The UI labels
both clearly ("SIMULATED rules — not Decider 2B", "demo-template"). Nothing is silently faked.

### Going live (real Decider 2B + Bedrock)
1. Decider: follow `docs/DECIDER_SETUP.md` (local model, ~4.5 GB base-weight download; CPU works but is slower; Windows users: WSL2 per the official docs). Then run `python scripts/check_decider.py` and confirm it prints `PARSED OK`.
2. Set `FLOWSAGE_DECIDER_MODE=live` in `.env`.
3. Bedrock: enable model access in the AWS console, set `BEDROCK_MODEL_ID` and `AWS_REGION`, sign in with the AWS CLI/SSO, set `FLOWSAGE_BEDROCK_MODE=live`. **Bedrock is billed per token**; each investigation makes one call (≤900 output tokens). Check current pricing for your model first. The Decider runs locally and has no per-call fee.

## Architecture

```
React UI ──► FastAPI (auth, rate limit, validation) ──► Service
                                                          │
                     ┌────────────────────────────────────┤
                     ▼                                    ▼
        Decision pattern (decider.py)             SQLite (users, incidents, audit)
   question + allowlisted options ─► Decider 2B
   validate ─► map to tool ─► tools.run_tool (allowlist)
                     │
                     ▼
        Explainer (Bedrock Converse, evidence-grounded, validated)
                     │
                     ▼
   App-defined recovery policy ─► human approval ─► simulated recovery
```

Key safety rules (all covered by tests): model output is validated against the option list; the app, not
the model, builds tool arguments; fail-closed on decider/tool errors (no tool runs); logs are untrusted data
(a prompt-injection line is seeded in the "scheduled failure" scenario); high-risk recovery needs approval;
every step is written to an audit table; every query is scoped to the signed-in user.

## Reusable decision pattern
See `docs/DECIDER_PATTERN.md` and `backend/flowsage/decider.py`.

## Decider confidence
`Decision.confidence` is filled **only** if the live server returns a `confidence` field; otherwise it is
`None` and the UI says "not provided by this backend". The simulated backend never invents one.

## Known limitations
- Local-demo security: no HTTPS/CSRF hardening, in-memory rate limiter, token in sessionStorage.
- The simulated decider is keyword rules for development only; its "accuracy" says nothing about Decider 2B.
- "Decision correctness" = match with the *app-defined* expected action per scenario (6 hand-written scenarios; not a benchmark).
- Bedrock model ids and pricing are intentionally not hardcoded; verify in your account.
- No PDF export (CSV and per-incident JSON only).

## Project tree
```
flowsage/
├─ backend/  flowsage/{config,scenarios,tools,decider,explain,orchestrator,db,auth,reports,service,api}.py
│            tests/test_flowsage.py   requirements.txt
├─ frontend/ src/{App.tsx,api.ts,ui.tsx,pages/{Public,Workspace}.tsx}  (Vite + React + TS + Tailwind)
├─ scripts/  setup.ps1 test.ps1 start.ps1 check_decider.py
├─ docs/     DECIDER_PATTERN.md DECIDER_SETUP.md ARTICLE_DRAFT.md VIDEO_STORYBOARD.md SUBMISSION_CHECKLIST.md TEST_RESULTS.txt
└─ .env.example  .gitignore  LICENSE (MIT)
```

## Troubleshooting (Windows)
- `running scripts is disabled`: `Set-ExecutionPolicy -Scope Process Bypass` then re-run.
- `python` not found: install Python 3.10+ and tick "Add to PATH".
- Login says "server secret not configured": start via `start.ps1` (it generates one) or set `FLOWSAGE_SECRET_KEY` (16+ chars).
- Port busy: change `--port` in `start.ps1` and the proxy in `frontend/vite.config.ts`.
- Bedrock 503 "BEDROCK_MODEL_ID is not configured": set it or switch `FLOWSAGE_BEDROCK_MODE=off`.
