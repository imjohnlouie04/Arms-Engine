# ARMS Generated Prompts

> Managed by ARMS Engine. Regenerated from `.arms/BRAND.md` during `arms init`.
> Update the brand brief and re-run `arms init` to refresh these prompts.

## Usage
- Read `.arms/CONTEXT_SYNTHESIS.md` first.
- These prompts stay intentionally thin so the synthesis file remains the single dense context source.
- Use the listed specialist agent for each prompt.
- Do not run specialist implementation prompts with `arms-main-agent`; keep `arms-main-agent` for orchestration only.

## Orchestrator Prompt
**Assigned Agent:** `arms-main-agent`
**Active Skill:** `arms-orchestrator`
**Copilot CLI:** `/agent arms-main-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md` first.
For arms-engine, review the current implementation and ship the highest-impact next improvement.
Use Next.js (latest stable) + shadcn/ui.
Honor: No hard constraints captured / No additional content or visual non-negotiables captured.
```

## Product Kickoff Prompt
**Assigned Agent:** `arms-product-agent`
**Copilot CLI:** `/agent arms-product-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md`.
Turn it into a concise charter for arms-engine.
Prioritize around Core features not yet captured and flag the highest-risk ambiguities early.
```

## DevOps Prompt
**Assigned Agent:** `arms-devops-agent`
**Active Skill:** `devops-orchestrator`
**Copilot CLI:** `/agent arms-devops-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md`.
audit the existing stack, tooling, and deployment path before changing infrastructure.
Keep the recommendation anchored to Supabase, Vercel, and Email/password or OAuth via Supabase Auth.
```

## Frontend Prompt
**Assigned Agent:** `arms-frontend-agent`
**Active Skill:** `ui-ux-pro-max`
**Copilot CLI:** `/agent arms-frontend-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md`.
review the current initial product experience and improve the highest-impact user flow.
Keep the UI aligned to Technical, precise, efficient / Direct, technical, low-fluff communication for builders. / Undecided - confirm preferred light/dark direction.
Structure around Use the most suitable structure for the project type and optimize for Define the primary conversion actions.
```

## Data Prompt
**Assigned Agent:** `arms-data-agent`
**Copilot CLI:** `/agent arms-data-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md`.
Review the current data model and identify the safest next schema changes.
Shape the work around Core features not yet captured and preserve explicit access boundaries.
```

## Backend Prompt
**Assigned Agent:** `arms-backend-agent`
**Active Skill:** `backend-system-architect`
**Copilot CLI:** `/agent arms-backend-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md`.
Review the current backend/auth implementation and patch the highest-risk gaps.
Use Supabase with auth shaped around Email/password or OAuth via Supabase Auth.
```

## Security Prompt
**Assigned Agent:** `arms-security-agent`
**Active Skill:** `security-code-review`
**Copilot CLI:** `/agent arms-security-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md`.
Review auth, access control, and secret handling for arms-engine.
Check Next.js + Supabase + shadcn/ui / Email/password or OAuth via Supabase Auth / Supabase and flag OWASP-relevant risks early.
```

## QA Prompt
**Assigned Agent:** `arms-qa-agent`
**Active Skill:** `qa-automation-testing`
**Copilot CLI:** `/agent arms-qa-agent`
```text
Read `.arms/CONTEXT_SYNTHESIS.md`.
Prepare the pre-flight validation plan for arms-engine.
Validate the primary initial product experience and core flows tied to Core features not yet captured; focus on regression risk and current production-critical flows.
```
