"""Run this on YOUR machine after `strands-decider serve ... --port 8099`.
Prints the RAW /v1/systemone response for a choice question and shows whether FlowSage can parse it.
This closes the one gap I could not verify: the exact JSON field names of a `choice` answer."""
import json, sys, urllib.request
sys.path.insert(0, "backend")
from flowsage.decider import StrandsDeciderClient
from flowsage.tools import ACTION_DESCRIPTIONS
url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8099"
state = ("Incident INC-1 (simulated). payment_verification request timeout after 30000ms. "
         "payment_status=UNKNOWN. order_confirmation blocked.")
body = {"state": state, "questions": {"next_action": {"type": "choice",
        "instructions": "Which single diagnostic action should run next?", "criteria": ACTION_DESCRIPTIONS}}}
req = urllib.request.Request(url + "/v1/systemone", json.dumps(body).encode(), {"content-type": "application/json"})
raw = json.loads(urllib.request.urlopen(req, timeout=60).read())
print("RAW RESPONSE:\n", json.dumps(raw, indent=2))
d = StrandsDeciderClient._parse(raw, "q", list(ACTION_DESCRIPTIONS), 0.0)
print("\nPARSED OK ->", d.selected, "| confidence:", d.confidence, "| fields seen:", d.raw_keys)
