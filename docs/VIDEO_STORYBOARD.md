# 3-minute demo storyboard (target 2:40)
0:00–0:15 Problem: a payment times out — did it succeed? Blind retry = duplicate charge. Show tagline.
0:15–0:35 Landing → Launch Demo → sign in. Say clearly: everything is simulated.
0:35–1:00 Incidents → generate "Payment verification timeout". Show workflow graph + raw logs.
1:00–1:50 Run investigation. Show timeline; open Decision Trace: question, allowed options, selected option, REAL Decider 2B confidence value (only if live), tool result.
1:50–2:15 Root cause & recovery: confirmed vs suspected, Bedrock explanation (source label visible), recovery = escalate, not retry.
2:15–2:35 Invalid-config scenario: high-risk fix needs approval → Approve → simulated result → audit history.
2:35–2:50 Reports: CSV export, decision quality from stored records. Close: repo + article links.
Rule: do not show the simulated backend while claiming Decider 2B.
