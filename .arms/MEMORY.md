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

- [PENDING APPROVAL][memory-20260615-01]: Capture the reusable implementation decision behind 'Fix arms init so empty projects still initiate project assessment' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260615-05]: Capture the preferred orchestration pattern that emerged while implementing 'Persist brand intake prompt so AI tools that summarize CLI output still show questionnaire' so future deep-dive work follows the same path.

## Project Context & MVP

- [PENDING APPROVAL][memory-20260615-02]: Capture the reusable implementation decision behind 'Fix arms init question output so empty projects visibly show the brand/context questionnaire' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260615-03]: Capture the reusable implementation decision behind 'Fix empty-project init so status shows brand intake questions and next action' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260615-04]: Capture the reusable implementation decision behind 'Investigate brand assessment CLI failures and cross-tool AI integration support' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260615-06]: Capture the reusable implementation decision behind 'Force AI tool summaries to display brand intake questions after arms init halt' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260615-07]: Capture the reusable implementation decision behind 'Design robust brand intake display flow that works despite AI command-output summarization' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260615-08]: Capture the reusable implementation decision behind 'Implement dedicated arms intake command to print and apply brand questionnaire' if this session establishes a pattern worth repeating.

## Primary Use Case & Implications

## Phase 2 Backlog

## Known Bugs & Fixes

- [APPROVED][memory-20260610-02]: When a sync target gains per-platform content variants (e.g. `model:` frontmatter on `.claude/agents/*.md` and `.gemini/agents/*.md` driven by `model_routing.yaml`), `arms doctor`'s `validate_agent_mirrors` check must build expected content with matching `platform=`/`routing=` args per mirror dir -- otherwise every agent mirror is reported as perpetually stale right after a clean sync.
