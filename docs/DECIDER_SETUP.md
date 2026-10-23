# Running the real Strands Decider 2B (verified from official README/docs, 14 Oct 2026)
- Install: `pip install strands-decider` (use a separate venv; it pulls torch).
- Serve: `strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --device cpu --port 8099`
  (v19 `StrandsAgents/strands-decider-2B-hobson-v19` is the model used in the official agent example.)
- First run downloads base weights `Qwen/Qwen3.5-2B-Base` (~4.5 GB). Check free disk space first.
- Windows: official docs describe WSL2 for NVIDIA GPU serving; CPU serving uses the same commands with `--device cpu` and is slower.
- The server binds to 127.0.0.1 with **no authentication** — local use only.
- Then: `python scripts/check_decider.py` and `FLOWSAGE_DECIDER_MODE=live`.
Model names/flags may change; re-check https://github.com/strands-labs/strands-decider.
