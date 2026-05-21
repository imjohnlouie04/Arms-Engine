# ARMS Project Memory

> Compressed Caveman Style. Keep dense. Keep executable.

[STATE] : shared project state -> `.arms/`; assistant config -> `.gemini/`
[MEMORY] : canonical project memory path -> `.arms/MEMORY.md`
[WORKFLOW] : workflow + reports + agent-outputs -> `.arms/` paths
[SKILLS] : valid skill = directory with `SKILL.md` -> discover + register + mark active
[BINDING] : explicit agent skill map from `agents.yaml` -> fallback inference for unbound new skills
[TASK TABLE] : stale `Active Skill` cells on re-init -> repair from agent binding + task-text relevance
[VERSION] : newer project session vs older engine -> block init unless dev checkout or `--allow-engine-downgrade`
[WATCH] : `arms init --watch` -> wait `.arms/BRAND.md` change -> rerun init -> refresh prompts

## Developer Preferences

- [PENDING APPROVAL][memory-20260513-02]: Capture the preferred orchestration pattern that emerged while implementing 'Fix Gemini CLI chat intake so normal messages create or refresh SESSION.md task rows' so future deep-dive work follows the same path.
- [PENDING APPROVAL][memory-20260513-03]: Capture the reusable implementation decision behind 'Release Gemini intake bridge fix' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260514-01]: Capture the reusable implementation decision behind 'Audit Gemini CLI thinking stall causes in this repo' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260514-02]: Capture the reusable implementation decision behind 'Move Gemini/Copilot instruction scaffolding to project-owned root files' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260514-03]: Capture the reusable implementation decision behind 'Release project-owned instruction scaffolding fix' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260514-04]: Capture the reusable implementation decision behind 'Fix mobile-only h-11 mandate wording across ARMS instruction surfaces' if this session establishes a pattern worth repeating.

## Project Context & MVP

- [PENDING APPROVAL][memory-20260513-01]: Capture the reusable implementation decision behind 'Scope mobile-first mandate so touch-target and table rules apply only to mobile layouts' if this session establishes a pattern worth repeating.

## Primary Use Case & Implications

## Phase 2 Backlog

## Known Bugs & Fixes
