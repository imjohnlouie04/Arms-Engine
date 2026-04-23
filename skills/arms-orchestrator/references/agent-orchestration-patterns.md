# Multi-Agent Orchestration Patterns

ARMS uses proven orchestration patterns from distributed systems and AI agent research. Understanding these patterns helps you extend ARMS or debug complex handoffs.

## Core Patterns in ARMS

### 1. Orchestrator-Worker (Primary Pattern)

**Structure:**

- `arms-main-agent` = orchestrator
- All other agents = workers

**Flow:**

1. Orchestrator receives task
2. Classifies intent and decomposes into subtasks
3. Delegates each subtask to specialized worker
4. Workers execute and report back
5. Orchestrator synthesizes results

**Why this pattern:**

- Clear ownership (orchestrator owns session state)
- Easy to debug (all coordination flows through one agent)
- Scalable (add workers without changing orchestrator logic)
- Predictable (no circular handoffs)

**Trade-offs:**

- Orchestrator is a potential bottleneck
- Less parallelization than decentralized patterns
- Requires orchestrator to understand all worker capabilities

### 2. Hierarchical Delegation (Secondary Pattern)

Used when a worker needs to delegate to sub-workers.

**Example:**

- `arms-frontend-agent` delegates to hypothetical `arms-ui-agent` for complex component work
- `arms-devops-agent` delegates to `arms-security-agent` for deployment audits

**Flow:**

1. Orchestrator delegates to worker
2. Worker determines subtask requires specialist
3. Worker delegates to sub-worker
4. Sub-worker executes and reports to worker
5. Worker synthesizes and reports to orchestrator

**Why this pattern:**

- Reduces orchestrator complexity
- Allows domain-specific decomposition
- Workers maintain autonomy

**Trade-offs:**

- Deeper call stacks
- Harder to trace execution
- Risk of delegation loops if not carefully designed

### 3. Sequential Pipeline (Task Chains)

Used for workflows with strict ordering.

**Example: Full-Stack Feature**

1. `arms-data-agent` → creates schema migration
2. `arms-backend-agent` → builds API endpoints
3. `arms-frontend-agent` → builds UI components
4. `arms-qa-agent` → writes tests
5. `arms-devops-agent` → prepares deployment

**Flow:**

Orchestrator executes agents in sequence, passing output of each as input to next.

**Why this pattern:**

- Natural for dependency chains
- Easy to visualize
- Clear failure points

**Trade-offs:**

- No parallelization
- Slowest agent blocks entire pipeline
- Rigid — hard to adapt to changing requirements mid-execution

### 4. Parallel Execution (Independent Tasks)

Used when tasks have no dependencies.

**Example: Pre-Deployment Checks**

- `arms-qa-agent` runs tests
- `arms-security-agent` audits dependencies
- `arms-devops-agent` validates environment configs

All run simultaneously, orchestrator waits for all to complete.

**Why this pattern:**

- Fastest for independent tasks
- Efficient use of resources

**Trade-offs:**

- Requires careful identification of true independence
- More complex error handling (partial failures)
- Higher cognitive load for developer reviewing results

## Handoff Mechanics

### Explicit Handoffs

Orchestrator explicitly delegates:

```
[arms-main-agent]: Delegating to arms-backend-agent for API implementation.
```

Worker explicitly reports back:

```
[arms-backend-agent]: Task complete. Reporting back to arms-main-agent.
```

**Why explicit:**

- Developer always knows who's "speaking"
- Clear audit trail in SESSION.md
- Easy to debug handoff failures

### Implicit Context Passing

Agents read shared state (SESSION.md, MEMORY.md) without explicit parameter passing.

**Why implicit:**

- Reduces verbosity
- Agents can discover context they need
- Easier to add new context fields without updating all agents

**Trade-offs:**

- Harder to track what each agent actually reads
- Risk of stale data if SESSION.md not updated
- Requires discipline to keep shared state clean

## Approval Gates

Approval gates are **blocking handoffs** — orchestrator cannot proceed until user confirms.

**When to use:**

- Before executing irreversible actions (deploy, database migration)
- Before major architectural decisions (tech stack choice)
- When user input is ambiguous
- When cost/time implications are significant

**Implementation:**

Orchestrator presents options/plan, then:

```
[Next Step]: Awaiting approval. HALT
```

No agent executes until user responds.

**Why HALT pattern:**

- Prevents runaway execution
- Keeps developer in control
- Reduces risk of unwanted changes

## State Management

### SESSION.md (Ephemeral State)

- Active tasks
- Current handoffs
- In-progress work
- Pruned regularly

### MEMORY.md (Persistent State)

- Architectural decisions
- Developer preferences
- Known bugs and fixes
- Lessons learned
- Never pruned (only appended)

### agents.yaml (Agent Registry)

- Agent roster
- Agent capabilities
- Agent dependencies

**Why separate files:**

- Different update frequencies
- Different pruning policies
- Easier to reason about what each file contains

## Quality Gates

Quality gates are **automated checks** before task completion.

**Pre-Flight QA (before "done"):**

1. `npm run build` (or equivalent)
2. `npm run lint`
3. `npm run type-check`
4. `npm run test` (if tests exist)

If any fail, task is NOT complete.

**Why automated:**

- Catches errors before commit
- Enforces standards without manual review
- Reduces back-and-forth

**When to skip:**

- Explicitly requested by user ("skip tests for now")
- Early prototyping phase
- Tests don't exist yet (but flag this as technical debt)

## Coordination Challenges

### Challenge 1: Circular Handoffs

**Problem:**

- Agent A delegates to Agent B
- Agent B delegates back to Agent A
- Infinite loop

**Solution:**

- Orchestrator tracks handoff chain
- Blocks handoffs that would create cycle
- If cycle detected, escalate to orchestrator for re-planning

### Challenge 2: Context Loss

**Problem:**

- Agent A has context from earlier in conversation
- Agent B doesn't have that context
- Agent B makes incorrect assumptions

**Solution:**

- All critical context goes in SESSION.md
- Agents read SESSION.md before executing
- Orchestrator summarizes context in delegation message

### Challenge 3: Conflicting Updates

**Problem:**

- Agent A updates file X
- Agent B also updates file X
- Changes conflict

**Solution:**

- Sequential execution for overlapping concerns
- Orchestrator identifies potential conflicts in task table
- Explicit handoff order prevents conflicts

### Challenge 4: Partial Failures

**Problem:**

- Agent A completes successfully
- Agent B fails
- System is in inconsistent state

**Solution:**

- Git checkpoint before multi-step workflows
- Rollback on failure
- Orchestrator decides: retry, skip, or abort

## Extending ARMS

### Adding a New Agent

1. Define agent's domain and capabilities
2. Add to `agents.yaml`
3. Update orchestrator's delegation logic
4. Define handoff protocol (what context does new agent need?)
5. Add to relevant pipelines (e.g., pre-deployment checks)

**Example: Adding `arms-analytics-agent`**

Domain: Analytics integration (Google Analytics, Mixpanel, etc.)

Capabilities:

- Add tracking code
- Define events
- Set up conversion funnels

Handoff protocol:

- Receives: list of pages/components to track
- Returns: tracking implementation + event schema

### Creating Custom Orchestration Logic

For advanced users who need orchestration beyond default patterns:

1. Define custom workflow in `SESSION.md`
2. Orchestrator reads workflow and executes
3. Use "Custom" task type in task table

**Example: A/B Test Deployment**

1. `arms-frontend-agent` creates variant components
2. `arms-devops-agent` sets up feature flags
3. `arms-analytics-agent` defines success metrics
4. `arms-devops-agent` deploys with gradual rollout
5. `arms-analytics-agent` monitors metrics

This workflow doesn't fit standard patterns, so orchestrator executes custom sequence.

## Research References

ARMS orchestration patterns are informed by:

- **Microsoft's AI Agent Design Patterns** (2026): Orchestrator-worker, hierarchical, and group chat patterns
- **OpenAI Swarm**: Lightweight handoff patterns for decentralized coordination
- **LangGraph**: Graph-based workflows with typed state channels
- **CrewAI**: Role-based agent teams with built-in delegation
- **Multi-Agent Systems research**: Coordination protocols, message passing, distributed consensus

## Key Takeaways

1. **Orchestrator-worker is ARMS's primary pattern** — centralized coordination, specialized workers
2. **Explicit handoffs** make debugging easier
3. **Approval gates** keep developer in control
4. **Quality gates** catch errors before commit
5. **State management** (SESSION.md vs. MEMORY.md) prevents context loss
6. **Sequential pipelines** for dependencies, **parallel execution** for independence
7. **Avoid circular handoffs** — orchestrator must prevent cycles

---

**Understanding these patterns helps you use ARMS effectively and extend it for your specific needs.**