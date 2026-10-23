# FlowSage — Environmental Decision Support Agent

FlowSage is an AI-powered environmental decision-support project designed to help evaluate environmental situations, identify potential risks, and recommend safer next steps.

## Problem Statement

Environmental concerns can involve incomplete evidence, uncertain observations, and potentially unsafe actions. People need guidance that distinguishes supported conclusions from assumptions and identifies situations requiring human review.

## Our Solution

FlowSage combines environmental scenario analysis with decision-support logic and safety guardrails.

### Key Features

- **Evidence grounding:** Encourages decisions to be supported by available evidence.
- **Safety-aware guidance:** Helps identify potentially unsafe actions.
- **Human review:** Supports escalation when a situation is uncertain or requires expert assessment.
- **Decision explanations:** Designed to make recommendations easier to understand.
- **Testable architecture:** Includes automated tests and evaluation scenarios.

## Technology

The project includes Python-based agent and decision components, a web application, and integration points for Strands Decider.

## Project Structure

- `agent/` — Agent logic, decision guardrails, tools, and evaluation cases.
- `backend/` — Backend application and supporting services.
- `frontend/` — Web interface.
- `docs/` — Technical documentation and project notes.
- `scripts/` — Setup, testing, and development scripts.

## Testing

The development kit's automated test suite previously passed 38 tests. This result verifies those tests only; it does not establish that live AWS deployment or Strands Decider integration is working.

## Setup

Refer to the setup and integration documentation in `docs/` and the project's setup scripts. Review the required environment variables and dependencies before running the application.

## Current Limitations

- Live Strands Decider integration has not yet been verified.
- AWS deployment has not yet been verified.
- Environmental recommendations should not replace qualified environmental professionals, emergency services, or official guidance.
- Evaluation results must be generated and verified for this specific project before reporting performance metrics.

## Responsible Use

FlowSage is a decision-support prototype. It should communicate uncertainty, avoid unsupported accusations, and recommend human review when evidence is insufficient or risks are significant.

## Project Status

Prototype under development. Automated tests have passed; live integration and deployment remain to be verified.

## Repository

Source code: https://github.com/bobbilimeghana2007/FlowSage
