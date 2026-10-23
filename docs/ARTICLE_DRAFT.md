# FlowSage AI: Building a Self-Healing Workflow Agent with Strands Decider 2B and Amazon Bedrock
*DRAFT — tags: #strands-decider-2b #tool-selection (verify). Replace every [PLACEHOLDER] with measured data; add real screenshots only.*

## 1. Hero
A workflow fails at 2 a.m. Which check should run first? FlowSage AI hands that one decision to a small decision model and keeps everything else under application control.

## 2. The real workflow failure
Order Received → Payment Verification → Order Confirmation → Dispatch. Payment verification times out; confirmation is blocked.

## 3. Why a normal retry is not always safe
After a timeout the payment may have been captured. A retry can double-charge. The correct first step is to check payment status.

## 4. The solution
Evidence → constrained decision → allowlisted tool → grounded explanation → human approval → simulated recovery. (All data synthetic.)

## 5. Architecture
[Insert the diagram from README, labelled "architecture as implemented" only after you confirm it matches the running app.]

## 6. The reusable Decider 2B pattern
Typed question, five allowlisted options, validation, tool mapping, audit. Code: `backend/flowsage/decider.py`. [Add InterventionHandler wiring once verified.]

## 7. A real end-to-end investigation
[Paste real Decision Trace screenshot. Real Decider output: selected=[ACTUAL], confidence=[ACTUAL], latency=[ACTUAL ms].]

## 8. Evidence-based explanation
Bedrock receives only collected evidence and must quote it verbatim; ungrounded evidence is dropped; malformed output is rejected and shown as an error.

## 9. Human approval and safe recovery
High-risk recovery requires approval; every action is audited; execution is a reversible simulation.

## 10. Security and limitations
Prompt-injection line seeded in logs; fail-closed design; local-demo auth only; simulated data only; 6 hand-written scenarios.

## 11. Testing and verified results
Backend: 41 automated tests passed (stdlib unittest). Real-service results: [PLACEHOLDER until measured]. Decision accuracy on the 5 failing scenarios with real Decider 2B: [PLACEHOLDER]/5.

## 12. Lessons learned
[Write from your own experience.]

## 13. Links
Repo: [URL]  Video: [URL]
