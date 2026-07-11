# ARMS Command Cheat Sheet 🚀

Use these commands to interact with the **Global ARMS Orchestrator**.

## Initialization Commands
| Command | Action |
|---|---|
| `init` | Standard boot sequence. Generates a Task Table and **HALTS** for approval. |
| `init yolo` | **Full Automation Mode.** Generates a Task Table and immediately begins execution without halting. |
| `init compress` | Initializes and then uses the **Caveman Skill** to shrink session and memory files for token efficiency. |
| `init --watch` | Waits on `.arms/BRAND.md` and automatically reruns init when the brand brief changes. |
| `intake` | Runs the architecture assessment on its own: asks the compact questions interactively in a real terminal, or prints the answer block for chat. Also how the AI applies a researched Stack Proposal (`intake --answers-text "<block>"`). |
| `init --no-interactive` | Skips the terminal questionnaire prompt and prints the intake block instead. |

Brand bootstrap behavior during `init`:
- Existing project with no brand file: ARMS inspects the repo and drafts `.arms/BRAND.md`.
- New / empty project: ARMS writes a question-driven `.arms/BRAND.md` template, then **proceeds with fallback brand values** — synthesis, prompts, and the seeded startup task table generate immediately without halting. The assessment is non-blocking by default (`BRAND_INTAKE_GATE_ENABLED = False` in `arms_engine/brand.py`).
- While the stack is unresearched, ARMS also writes `.arms/RESEARCH_BRIEF.md`: the host AI should offer the assessment questions conversationally, then **web-search the best-fit stack for the answers** (any stack — not just the ARMS presets) and apply the returned Stack Proposal with `arms intake --answers-text`. Re-running `arms init` retargets synthesis, prompts, and the pending scaffold task to the researched stack; concrete non-preset stacks (e.g. `SvelteKit + Supabase + Skeleton UI`) are honored as-is.
- To capture Brand Context later, run `arms intake` — in a real terminal it asks the compact questions one-by-one on stdin; otherwise it prints the answer block for a chat reply. `--no-interactive` skips the stdin prompt.
- When the intake gate is re-enabled, `init` halts on the questionnaire for new projects; re-running `init` after filling `.arms/BRAND.md` resumes from that checkpoint, and `init --watch` resumes automatically after `.arms/BRAND.md` changes.
- When the brand brief is complete, `init` generates `.arms/CONTEXT_SYNTHESIS.md`, refreshes `.arms/GENERATED_PROMPTS.md`, and seeds the startup task table if it is still empty.
- Stack shortcuts use the current latest-stable recommendation set: `A` = Next.js + Supabase + shadcn/ui, `B` = Nuxt + Firebase + Nuxt UI, `C` = Astro + Tailwind CSS + DaisyUI, `D` = Custom.
- Landing-page media guidance now routes through `nano-banana-pro` and expects at least five production-ready images, including showcase / best-work imagery where it makes sense.
- `init` also accepts `--preset <name>` to prefill common defaults (`local-business`, `saas`, `portfolio`, `ecommerce`, `content-site`).
- `init --answers-file path/to/answers.md` and `init --answers-text "Mission: ..."` apply structured answers directly into `.arms/BRAND.md`.
- `intake --answers-file path/to/answers.md` and `intake --answers-text "Project Name: ..."` apply structured answers without running the full init sync.

## Execution Commands (Post-Init)
| Command | Action |
|---|---|
| Chat issue / work request in CLI or IDE | ARMS should immediately create or refresh the matching `.arms/SESSION.md` row using `arms task log --task "<normalized ask>"` semantics before substantive planning or implementation. |
| `task log` / `task update` / `task done` | Executable task ledger. Auto-routes the task to the right specialist (keyword pass + scored fallback), auto-fills `Active Skill` and `Model` tier, and emits an explicit **Handoff** line telling each AI tool how to delegate (Claude Code Task-tool subagent / Copilot `/agent`). |
| `yolo` | Activates **Fast-Track Execution** for the currently approved Task Table. |
| `run status` | Dumps the current pipeline phase, active tasks, and blockers from `SESSION.md`. |
| `run review` | Triggers a full audit (QA, Security, Frontend) and generates a report. |
| `fix issues` | Parses the latest review report and generates a Task Table to apply fixes. |
| `run pipeline` | Executes **Review → Fix → Deploy** in one sequence with approval gates between each phase. |

## Power Features (Automatic)
- **Flash Recovery:** YOLO mode will automatically try to fix minor lint/type errors **once** before stopping.
- **Auto-Critique:** `arms-qa-agent` must verify every task before it is marked as `Done`.
- **Global Linker:** Every `init` command automatically runs `init-arms.sh`, which preserves the caller's `PYTHONPATH` and hands off to `python3 -m arms_engine.init_arms` using the current engine checkout.

---
*ARMS orchestrates. You decide.*
