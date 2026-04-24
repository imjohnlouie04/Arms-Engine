# ARMS GLOBAL PROTOCOL: CODE REVIEW
**Primary Executors:** `arms-qa-agent`, `arms-security-agent`, `arms-frontend-agent`

## Overview
This protocol defines the strict evaluation criteria for the `run review` or `run pipeline` command. Agents must analyze the local project state and source code against these global standards before generating the local review report.

---

## Phase 1: Architecture & Code Quality (`arms-qa-agent`)
The QA agent will audit the codebase for structural integrity and defensive coding practices.

* **TypeScript Strictness:** Verify that TypeScript strict mode is enabled and enforced across all new code. Flag any explicit `any` types or suppressed type warnings.
* **Component Syntax:** Enforce absolute adherence to `<script setup>` syntax for all Vue/Nuxt components. Flag any legacy Options API or standard Composition API setups.
* **State & Memory Management:** Audit state logic for memory-safe execution. Require the use of reliable utilities (like VueUse) for event listeners, window sizing, and side effects to prevent memory leaks.
* **Immutability Guardrails:** Scan the current working tree for any modifications to core modules, specifically `Gatekeeper` logic or `Holiday Pay` computation engines. If these files are touched without explicit, overriding user directives, flag them as a critical violation and revert.

## Phase 2: Responsive & UI Standards (`arms-frontend-agent`)
The frontend agent will audit the UI implementation to ensure it meets the ARMS mobile-first directives.

* **Mobile Extended Mandate:** Verify that portrait tablets (e.g., iPad Mini) are correctly classified as "Mobile Extended." Ensure these viewports utilize single-column layouts and stacked controls for touch targets.
* **Sidebar Breakpoints:** Audit grid definitions and component visibility classes. Ensure desktop sidebars strictly activate at the `xl` (1280px) breakpoint. Flag any layouts using `lg` (1024px) for sidebar triggers as failures.
* **Pre-flight Checks:** Ensure all frontend builds pass the local linter and type-checker before the review is marked complete.

## Phase 3: Security & Configuration (`arms-security-agent`)
The security agent will perform a vulnerability and configuration audit.

* **Environment Variables:** Scan for accidental inclusion of real `.env` files or hardcoded production API keys. Only `.env.local` or `.env.example` are permitted.
* **Authentication & Data:** Verify that token anti-tampering logic and secure biometric verification flows are intact. Check that all database tables have Row Level Security (RLS) policies actively enforced.
* **Dependency Audit:** Run a lightweight audit on `package.json` for known high-severity vulnerabilities.

---

## Phase 4: Output & Handoff
1.  **Generate Report:** The agents must synthesize their findings and write them to `./.gemini/reports/review-<YYYY-MM-DD>.md` in the local project directory.
2.  **Session Update:** Log the completion of the review phase in `./.gemini/SESSION.md`.
3.  **Approval Gate:** Present the summarized findings to the user and request permission to proceed.

> **Execution Mandate:** End the review phase with the following prompt: 
> *"Review complete and logged to `./.gemini/reports/`. Shall I pass these findings to the `FIX_ISSUE_PROTOCOL` for automated resolution?"* -> **HALT**