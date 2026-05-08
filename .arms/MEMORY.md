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

- [PENDING APPROVAL][memory-20260507-01]: Capture the preferred orchestration pattern that emerged while implementing 'Investigate repeated arms init startup task regeneration and report-driven next-step suggestions' so future deep-dive work follows the same path.
- [PENDING APPROVAL][memory-20260507-02]: Capture the reusable implementation decision behind 'Implement report-driven next-step recommendations during arms init' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260507-03]: Capture the preferred orchestration pattern that emerged while implementing 'Implement one-time startup task seeding markers for arms init' so future deep-dive work follows the same path.
- [PENDING APPROVAL][memory-20260507-04]: Capture the preferred orchestration pattern that emerged while implementing 'Improve startup task refresh and dedupe matching during arms init' so future deep-dive work follows the same path.
- [PENDING APPROVAL][memory-20260507-05]: Capture the reusable implementation decision behind 'Surface next recommended step in arms init output and monitor HUD' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260508-01]: Capture the reusable implementation decision behind 'Mirror ARMS orchestration intake instructions into Copilot project-owned instructions' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260508-02]: Capture the reusable implementation decision behind 'Commit, push, and release the init UX and Copilot instruction updates with a version bump' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260508-03]: Capture the preferred orchestration pattern that emerged while implementing 'Fix task logging so assigned sub-agent and skill are accepted and persisted' so future deep-dive work follows the same path.
- [PENDING APPROVAL][memory-20260508-04]: Capture the reusable implementation decision behind 'Add automated discrepancy checks so ARMS catches instruction drift between mirrored guidance' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260508-05]: Capture the reusable implementation decision behind 'Review ARMS engine for discrepancies' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260508-06]: Capture the reusable implementation decision behind 'Fix ARMS engine discrepancy audit findings' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260508-07]: Capture the preferred orchestration pattern that emerged while implementing 'Centralize ARMS protocol metadata and add drift tests' so future deep-dive work follows the same path.
- [PENDING APPROVAL][memory-20260508-08]: Capture the reusable implementation decision behind 'Commit, push, and bump ARMS engine version for metadata alignment changes' if this session establishes a pattern worth repeating.
- [PENDING APPROVAL][memory-20260508-09]: Capture the reusable implementation decision behind 'Commit and push remaining ARMS engine local changes' if this session establishes a pattern worth repeating.
