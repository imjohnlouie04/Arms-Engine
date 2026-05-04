# Testing Strategy

> Read by: arms-qa-agent
> Triggered by: `run review`, pre-flight checks, any test-related task

---

## Stack Defaults

| Project Type | Unit/Integration | E2E |
|---|---|---|
| Next.js | Vitest + React Testing Library | Cypress (default) / Playwright when required |
| Nuxt | Vitest + @nuxt/test-utils | Cypress (default) / Playwright when required |
| Astro | Vitest | Cypress (default) / Playwright when required |

---

## Setup

### Vitest (Next.js)
```bash
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      thresholds: { lines: 70, functions: 70, branches: 60 }
    }
  }
})
```

```ts
// src/test/setup.ts
import '@testing-library/jest-dom'
```

Use Cypress as the default browser E2E runner. Choose Playwright only for cross-browser, multi-tab, multi-origin, OAuth, or other flows that Cypress cannot cover cleanly. Do not install or configure Playwright by default when the project does not already depend on it.

### Cypress
```bash
npm install -D cypress
```

```ts
// cypress.config.ts
import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
  },
})
```

### Playwright (opt-in)
Only use this setup when the project is already configured for Playwright or when the test scope explicitly requires Playwright-only capabilities. If browser E2E is failing due to setup instability, de-escalate back to Cypress.

```bash
npm install -D @playwright/test
npx playwright install chromium
```

```ts
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  }
})
```

---

## Coverage Thresholds

| Project Phase | Lines | Functions | Branches |
|---|---|---|---|
| MVP / Early | 50% | 50% | 40% |
| Stable / Pre-launch | 70% | 70% | 60% |
| Production-critical | 80% | 80% | 70% |

arms-qa-agent flags coverage below threshold in SESSION.md. Deploy does not block on coverage alone unless explicitly configured — but gaps are always reported.

---

## What to Test

### Unit Tests — Always Cover
- Utility functions and helpers
- Data transformation logic
- Form validation logic
- Auth helper functions (token parsing, role checks)
- API response mappers

### Integration Tests — Cover for Core Flows
- API route handlers (mock Supabase client)
- Auth middleware behavior
- Database query functions with test DB

### E2E Tests — Cover Critical Paths
```
[ ] User can sign up and verify email
[ ] User can log in and log out
[ ] Protected routes redirect unauthenticated users
[ ] Core CRUD flow (create, read, update, delete primary entity)
[ ] Payment/subscription flow (if applicable)
[ ] Error states render correctly (404, 500, network error)
```

---

## Test Patterns

### API Route Test (Vitest)
```ts
import { describe, it, expect, vi } from 'vitest'
import { GET } from '@/app/api/users/route'

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() => ({
    from: vi.fn(() => ({
      select: vi.fn().mockResolvedValue({ data: [{ id: '1' }], error: null })
    }))
  }))
}))

describe('GET /api/users', () => {
  it('returns users', async () => {
    const response = await GET(new Request('http://localhost/api/users'))
    const data = await response.json()
    expect(response.status).toBe(200)
    expect(data).toHaveLength(1)
  })
})
```

### Auth E2E Test (Playwright opt-in)
```ts
import { test, expect } from '@playwright/test'

test('authenticated user can access dashboard', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('test@example.com')
  await page.getByLabel('Password').fill('password123')
  await page.getByRole('button', { name: 'Log In' }).click()
  await expect(page).toHaveURL('/dashboard')
})

test('unauthenticated user is redirected', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL('/login')
})
```

---

## Pre-Flight QA Sequence

arms-qa-agent runs this in order before marking any task complete:

```bash
# 1. Type check
npx tsc --noEmit

# 2. Lint
npm run lint

# 3. Unit + integration tests
npx vitest run --coverage

# 4. Build
npm run build

# 5. E2E (if staging environment available)
npm run test:e2e
# Use Cypress by default. Use Playwright only when the project is explicitly configured for it.
```

**Pass criteria:**
- Zero TypeScript errors
- Zero lint errors (warnings logged, do not block)
- All tests passing
- Build succeeds
- Coverage at or above threshold for current phase

Any failure → log in SESSION.md with specific error → escalate to arms-main-agent → do NOT mark task complete

---

## Technical Debt Flags

Log these in MEMORY.md when encountered, do not block on them:

```
- No tests exist yet for <module> — schedule before launch
- Coverage below threshold in <area> — acceptable for MVP, revisit pre-launch
- E2E tests skipped — no staging environment configured
```
