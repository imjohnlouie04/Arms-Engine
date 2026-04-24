# ARMS Command Cheat Sheet 🚀

Use these commands to interact with the **Global ARMS Orchestrator**.

## Initialization Commands
| Command | Action |
|---|---|
| `init` | Standard boot sequence. Generates a Task Table and **HALTS** for approval. |
| `init yolo` | **Full Automation Mode.** Generates a Task Table and immediately begins execution without halting. |
| `init compress` | Initializes and then uses the **Caveman Skill** to shrink session and memory files for token efficiency. |

Brand bootstrap behavior during `init`:
- Existing project with no brand file: ARMS inspects the repo and drafts `.arms/BRAND.md`.
- New / empty project: ARMS writes a question-driven `.arms/BRAND.md` for the user to complete.

## Execution Commands (Post-Init)
| Command | Action |
|---|---|
| `yolo` | Activates **Fast-Track Execution** for the currently approved Task Table. |
| `run status` | Dumps the current pipeline phase, active tasks, and blockers from `SESSION.md`. |
| `run review` | Triggers a full audit (QA, Security, Frontend) and generates a report. |
| `fix issues` | Parses the latest review report and generates a Task Table to apply fixes. |
| `run pipeline` | Executes **Review → Fix → Deploy** in one sequence with approval gates between each phase. |

## Power Features (Automatic)
- **Flash Recovery:** YOLO mode will automatically try to fix minor lint/type errors **once** before stopping.
- **Auto-Critique:** `arms-qa-agent` must verify every task before it is marked as `Done`.
- **Global Linker:** Every `init` command automatically runs `init-arms.sh` to sync the Global Engine with your project.

---
*ARMS orchestrates. You decide.*
