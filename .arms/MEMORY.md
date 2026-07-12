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

- [APPROVED][memory-20260711-01]: Capture the reusable implementation decision behind 'Auto-detect CLI environment and tailor handoff delegation hint and model details' if this session establishes a pattern worth repeating.
- [APPROVED][memory-20260711-02]: Capture the reusable implementation decision behind 'Remove deprecated Gemini CLI support and update instructions to focus on Google Antigravity' if this session establishes a pattern worth repeating.
- [APPROVED][memory-20260712-01]: Capture the preferred orchestration pattern that emerged while implementing 'Fix Codex delegation wait loop repeatedly reporting no agents completed and ensure delegated' so future deep-dive work follows the same path.

## Project Context & MVP

## Primary Use Case & Implications

## Phase 2 Backlog

## Known Bugs & Fixes

- [APPROVED][memory-20260610-02]: When a sync target gains per-platform content variants (e.g. `model:` frontmatter on `.claude/agents/*.md` and `.gemini/agents/*.md` driven by `model_routing.yaml`), `arms doctor`'s `validate_agent_mirrors` check must build expected content with matching `platform=`/`routing=` args per mirror dir -- otherwise every agent mirror is reported as perpetually stale right after a clean sync.
