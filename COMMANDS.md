# ARMS Command Cheat Sheet 🚀

Use these commands to interact with the **Global ARMS Orchestrator**.

## Initialization Commands
| Command | Action |
|---|---|
| `init` | Standard boot sequence. Generates a Task Table and **HALTS** for approval. |
| `init yolo` | **Full Automation Mode.** Generates a Task Table and immediately begins execution without halting. |
| `init compress` | Initializes and then uses the **Caveman Skill** to shrink session and memory files for token efficiency. |
| `init --watch` | Waits on `.arms/BRAND.md` and automatically reruns init when the brand brief changes. |

Brand bootstrap behavior during `init`:
- Existing project with no brand file: ARMS inspects the repo and drafts `.arms/BRAND.md`.
- New / empty project: ARMS writes a question-driven `.arms/BRAND.md`, including the initial tech stack fields plus a website / landing-page brief for content, marketing, and local-business projects, prints the questionnaire in the CLI, and halts for the user's answers.
- After the user fills in `.arms/BRAND.md`, re-run `init` to resume from that checkpoint. Incomplete questionnaires stay active instead of being treated as finished state.
- `init --watch` keeps the process alive at that checkpoint and resumes automatically after `.arms/BRAND.md` changes.
- When the brand brief is complete, `init` generates `.arms/CONTEXT_SYNTHESIS.md`, refreshes `.arms/GENERATED_PROMPTS.md`, and seeds the startup task table if it is still empty.
- Stack shortcuts use the current latest-stable recommendation set: `A` = Next.js + Supabase + shadcn/ui, `B` = Nuxt + Firebase + Nuxt UI, `C` = Astro + Tailwind CSS + DaisyUI, `D` = Custom.
- Landing-page media guidance now routes through `nano-banana-pro` and expects at least five production-ready images, including showcase / best-work imagery where it makes sense.
- `init` also accepts `--preset <name>` to prefill common defaults (`local-business`, `saas`, `portfolio`, `ecommerce`, `content-site`).
- `init --answers-file path/to/answers.md` and `init --answers-text "Mission: ..."` apply structured answers directly into `.arms/BRAND.md`.

## Execution Commands (Post-Init)
| Command | Action |
|---|---|
| Chat issue / work request in CLI or IDE | ARMS should immediately create or refresh the matching `.arms/SESSION.md` row using `arms task log --task "<normalized ask>"` semantics before substantive planning or implementation. |
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
