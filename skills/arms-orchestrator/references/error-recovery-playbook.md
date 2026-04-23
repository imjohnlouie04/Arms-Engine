# Error Recovery Playbook

> Read by: arms-main-agent, arms-devops-agent
> Triggered by: any agent failure, partial pipeline failure, deploy rollback

---

## Recovery Hierarchy

When something fails, arms-main-agent follows this order:
1. **Stop** — halt all in-progress agent tasks
2. **Assess** — determine scope of failure (which agents, which files affected)
3. **Checkpoint state** — commit or stash current working state
4. **Present** — surface failure + proposed recovery path to user → **HALT**
5. **Execute** — only after user confirms recovery approach

Never silently retry or self-heal a major failure. Always surface it.

---

## Agent Failure Scenarios

### Single Agent Fails (Parallel Mode)
**Problem:** One agent in a parallel batch returns an error or blocker.
**Response:**
1. Let other agents in the batch complete
2. Collect all results
3. Flag the failed agent's task in SESSION.md as `BLOCKED`
4. Present unified output with failure highlighted → **HALT**
5. Options to offer user: retry that agent, skip task, reassign to different agent

### All Agents Fail (Parallel Mode)
**Problem:** API unavailable or session context corrupted.
**Response:**
1. Checkpoint current git state: `git stash`
2. Log failure to SESSION.md with timestamp and error
3. Surface raw error to user → **HALT**
4. Suggest: wait and retry, reduce batch size, switch to Mode B (simulated)

### Simulated Agent Fails (API Mode)
**Problem:** Anthropic API call returns error or malformed response.
**Response:**
```javascript
// Retry logic for API calls
const callWithRetry = async (fn, maxRetries = 2) => {
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn()
    } catch (err) {
      if (i === maxRetries) throw err
      await new Promise(r => setTimeout(r, 1000 * (i + 1))) // exponential backoff
    }
  }
}
```
If still failing after retries → log to SESSION.md → surface to user → **HALT**

### Agent Returns Malformed Response
**Problem:** Agent response doesn't follow strict response template.
**Response:**
1. Log the raw response to SESSION.md under `## Malformed Responses`
2. Re-queue the task with explicit instruction to follow the template
3. If second attempt also malformed → escalate to arms-main-agent, do not proceed

---

## Pipeline Failure Scenarios

### `run review` Partial Failure
**Problem:** One reviewer agent (QA, Security, or Frontend) fails mid-review.
**Response:**
1. Collect results from agents that did complete
2. Mark incomplete agents as `INCOMPLETE` in review report
3. Present partial report with gaps clearly labelled → **HALT**
4. Do not proceed to `fix issues` with an incomplete review

### `fix issues` Fails Mid-Execution
**Problem:** Fix task causes new errors (build breaks, test regressions).
**Response:**
1. Stop remaining fix tasks immediately
2. Run `git diff` to show what changed
3. Determine: revert all, revert partial, or patch forward
4. Present options to user → **HALT**

### `run deploy` Fails
See Deploy Rollback section below.

---

## Deploy Rollback

### Vercel Rollback
```bash
# List recent deployments
vercel ls

# Rollback to previous deployment
vercel rollback <deployment-url>
```
Or via Vercel dashboard → Deployments → select previous → Promote to Production.

### Docker / VPS Rollback
```bash
# Stop current container
docker stop arms-app-container

# Run previous image (tag your images!)
docker run -d --name arms-app-container -p 3000:3000 \
  --env-file .env.production \
  arms-app:<previous-tag>
```

**This is why image tagging matters.** arms-devops-agent should tag every production image:
```bash
docker build -t arms-app:v1.2.0 -t arms-app:latest .
```

### Database Rollback (Supabase)
Supabase migrations are not automatically reversible. Prevention is the only reliable strategy:

```bash
# Before any migration, capture current state
supabase db dump -f supabase/backups/pre-migration-<date>.sql

# If rollback needed, restore from backup (destructive — confirm with user first)
psql <connection-string> < supabase/backups/pre-migration-<date>.sql
```

**Rule:** arms-data-agent must create a backup before any destructive migration (DROP, ALTER, bulk DELETE). Always surface this to user → **HALT** before executing.

---

## State Recovery

### SESSION.md Corrupted or Lost
```
1. Check SESSION_ARCHIVE.md for last known good state
2. Reconstruct active tasks from git log (recent commits show completed work)
3. Ask user to confirm current priorities
4. Reinitialize SESSION.md from scratch with confirmed state → HALT
```

### MEMORY.md Corrupted
```
1. Check git history: git log --follow .gemini/MEMORY.md
2. Restore last good version: git checkout <commit-hash> -- .gemini/MEMORY.md
3. Review restored content with user before proceeding → HALT
```

### Context Loss Mid-Session
If arms-main-agent loses track of what was delegated:
1. Read SESSION.md in full
2. Check git log for recent commits
3. List in-progress tasks to user and ask for confirmation of current state → **HALT**

---

## Failure Log Format

All failures logged to SESSION.md under `## Failures & Blockers`:

```markdown
## Failures & Blockers

### [timestamp] arms-qa-agent — Pre-flight failure
- **Error:** TypeScript strict mode — 3 type errors in src/lib/auth.ts
- **Status:** BLOCKED
- **Recovery:** Assigned to arms-frontend-agent for type fixes
- **Resolved:** [timestamp or PENDING]
```

---

## Escalation Path

| Failure Type | First Responder | Escalate To |
|---|---|---|
| Single agent error | arms-main-agent | User (if retry fails) |
| Build/type failure | arms-frontend-agent or arms-backend-agent | arms-main-agent |
| Test failure | arms-qa-agent | arms-main-agent |
| Security violation | arms-security-agent | arms-main-agent → User |
| Deploy failure | arms-devops-agent | arms-main-agent → User |
| Data/migration failure | arms-data-agent | arms-main-agent → User (always) |

Data and deploy failures always escalate to the user — no autonomous recovery on irreversible operations.
