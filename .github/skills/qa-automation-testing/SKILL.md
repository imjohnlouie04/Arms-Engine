---
name: qa-automation-testing
description: >
  Write robust, maintainable unit and E2E tests using Jest, Cypress, and Playwright.
  Use this for any testing task including writing new tests, debugging flaky tests,
  refactoring test suites, setting up test infrastructure, choosing testing strategies,
  creating fixtures and mocks, improving test performance, or reviewing test code.
  Also applies when working with test files, CI/CD test pipelines, test coverage,
  or when the user mentions testing, QA, quality assurance, pre-flight validation,
  test automation, Jest, Cypress, Playwright, test-driven development (TDD), or asks to add tests.
---

# QA Automation Testing

You're helping write production-grade automated tests for web applications. Focus on tests that catch real bugs, run reliably, and remain maintainable as the codebase evolves.

## Core Philosophy

**Test behavior, not implementation.** Users care about what the app does, not how it does it. Tests coupled to internal details break on every refactor.

**Isolation matters.** Each test runs independently with its own state. No shared data, no test ordering dependencies, no cascading failures.

**Flakiness is a bug.** A test that fails intermittently without code changes is worse than no test—it trains developers to ignore failures.

**Coverage is a side effect, not a goal.** Write tests for critical paths and edge cases that actually fail in production. Don't chase 100% coverage by testing trivial code or the language itself.

## Decision Tree: Which Tool?

### Jest (Unit & Integration)
- Pure logic: business rules, utilities, data transformations
- Component logic in isolation (with React Testing Library / Vue Test Utils)
- API endpoints, services, database queries (with mocking)
- Fast feedback loop—runs in milliseconds

### Playwright (E2E)
- Cross-browser requirements (Chromium, Firefox, WebKit)
- Complex multi-tab, multi-origin, or OAuth flows
- Large test suites needing parallel execution
- API testing alongside E2E (built-in request context)
- Mobile device emulation

### Cypress (E2E)
- Developer experience is the priority (time-travel debugger)
- Primarily Chrome/Chromium testing
- Teams new to E2E testing
- Component testing (more mature than Playwright's)

**Default: Use Jest for everything except full user journeys. Use Playwright for E2E unless Cypress's debugging experience is critical.**

## Jest Patterns

### Structure

```javascript
describe('OrderCalculator', () => {
  describe('calculateTotal', () => {
    it('applies discount to subtotal before tax', () => {
      const result = calculateTotal({ subtotal: 100, discount: 0.1, taxRate: 0.08 });
      expect(result).toBe(97.2); // (100 - 10) * 1.08
    });

    it('handles zero discount', () => {
      const result = calculateTotal({ subtotal: 100, discount: 0, taxRate: 0.08 });
      expect(result).toBe(108);
    });

    it('throws on negative subtotal', () => {
      expect(() => calculateTotal({ subtotal: -10, discount: 0, taxRate: 0.08 }))
        .toThrow('Subtotal must be positive');
    });
  });
});
```

**Nested `describe` blocks group related tests. Each `it` tests one specific behavior.**

### Mocking

Mock external dependencies, not internal implementation:

```javascript
// Good: Mock the external API
jest.mock('./api/paymentGateway');
import { processPayment } from './api/paymentGateway';

processPayment.mockResolvedValue({ success: true, transactionId: '123' });

// Bad: Mocking internal functions couples tests to implementation
jest.spyOn(orderService, '_calculateTax'); // Don't do this
```

**Mock at module boundaries. If you're mocking private methods, your module is probably too large.**

### Async Testing

```javascript
it('fetches user data', async () => {
  const user = await fetchUser(1);
  expect(user.name).toBe('Alice');
});

it('handles fetch errors', async () => {
  await expect(fetchUser(999)).rejects.toThrow('User not found');
});
```

### Fixtures

Create reusable test data factories:

```javascript
const createUser = (overrides = {}) => ({
  id: 1,
  name: 'Test User',
  email: 'test@example.com',
  role: 'user',
  ...overrides,
});

it('admins can delete posts', () => {
  const admin = createUser({ role: 'admin' });
  expect(canDelete(admin, post)).toBe(true);
});
```

## Playwright Patterns

### Locator Strategy (Most Important)

**Priority order:**

1. **Role-based:** `page.getByRole('button', { name: 'Submit' })`—mirrors user interaction and assistive tech
2. **Label/placeholder:** `page.getByLabel('Email')`, `page.getByPlaceholder('Enter email')`
3. **Test ID:** `page.getByTestId('checkout-button')`—stable but doesn't reflect user behavior
4. **CSS (last resort):** `.btn-primary`—brittle, breaks on style changes

**Never use:**
- Dynamic classes from CSS-in-JS: `.css-1x2y3z`
- Deep CSS selectors: `div > ul > li:nth-child(3) > a`
- XPath (unless absolutely necessary)

```javascript
// Good
await page.getByRole('button', { name: 'Add to Cart' }).click();
await expect(page.getByRole('status')).toContainText('Item added');

// Bad
await page.locator('.btn.btn-primary.add-cart').click();
await page.locator('#notification-3421').waitFor();
```

### Test Isolation

```javascript
import { test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  // Fresh state per test
  await page.goto('/dashboard');
});

test('user can create project', async ({ page }) => {
  await page.getByRole('button', { name: 'New Project' }).click();
  await page.getByLabel('Project Name').fill('Test Project');
  await page.getByRole('button', { name: 'Create' }).click();
  
  await expect(page.getByRole('heading', { name: 'Test Project' })).toBeVisible();
});
```

**Each test gets a fresh browser context—no cookies, localStorage, or session leakage.**

### Authentication Setup

Don't log in via UI in every test:

```javascript
// auth.setup.js
import { test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Log In' }).click();
  
  await page.context().storageState({ path: 'auth.json' });
});

// playwright.config.js
export default {
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.js/ },
    {
      name: 'chromium',
      use: { storageState: 'auth.json' },
      dependencies: ['setup'],
    },
  ],
};
```

**Log in once, reuse the session. Saves minutes per test run.**

### API Mocking

```javascript
await page.route('**/api/products', async (route) => {
  await route.fulfill({
    status: 200,
    body: JSON.stringify([{ id: 1, name: 'Widget', price: 29.99 }]),
  });
});

await page.goto('/shop');
await expect(page.getByText('Widget')).toBeVisible();
```

**Mock third-party APIs to avoid flakiness from external services.**

### Debugging

```javascript
// Pause execution
await page.pause();

// Screenshot on failure (automatic with trace: 'retain-on-failure')
await page.screenshot({ path: 'debug.png' });

// Trace viewer (playwright.config.js)
use: {
  trace: 'retain-on-failure',
}
```

**Run `npx playwright show-trace trace.zip` to replay test execution with DOM snapshots, network logs, and console output.**

## Cypress Patterns

### Commands

```javascript
cy.visit('/login');
cy.get('[data-testid="email"]').type('user@example.com');
cy.get('[data-testid="password"]').type('password');
cy.get('button[type="submit"]').click();

cy.url().should('include', '/dashboard');
cy.get('h1').should('contain', 'Welcome');
```

**Cypress auto-waits for elements. No manual `waitFor` needed.**

### Custom Commands

```javascript
// cypress/support/commands.js
Cypress.Commands.add('login', (email, password) => {
  cy.visit('/login');
  cy.get('[data-testid="email"]').type(email);
  cy.get('[data-testid="password"]').type(password);
  cy.get('button[type="submit"]').click();
});

// In tests
cy.login('user@example.com', 'password');
```

### Intercepts

```javascript
cy.intercept('POST', '/api/orders', {
  statusCode: 201,
  body: { orderId: 'abc123' },
}).as('createOrder');

cy.get('[data-testid="checkout-button"]').click();
cy.wait('@createOrder');
cy.get('[data-testid="confirmation"]').should('be.visible');
```

## Common Anti-Patterns

### Testing Implementation Details

```javascript
// Bad: Coupled to state variable names
expect(component.state.isLoading).toBe(false);

// Good: Test observable behavior
expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
```

### Brittle Selectors

```javascript
// Bad: Breaks when styling changes
page.locator('.MuiButton-root.MuiButton-containedPrimary');

// Good: Semantic selector
page.getByRole('button', { name: 'Submit' });
```

### Excessive Mocking

```javascript
// Bad: Mocking everything tests nothing
jest.mock('./calculateTax');
jest.mock('./applyDiscount');
jest.mock('./formatCurrency');
// Now you're just testing mock return values

// Good: Mock only external boundaries
jest.mock('./api/paymentGateway');
// Test real business logic
```

### Shared State

```javascript
// Bad: Tests depend on execution order
let user;

beforeAll(() => {
  user = createUser();
});

it('updates user name', () => {
  user.name = 'Alice'; // Mutates shared state
});

it('user has email', () => {
  expect(user.email).toBeDefined(); // Depends on previous test
});

// Good: Fresh state per test
beforeEach(() => {
  user = createUser();
});
```

### Happy Path Only

```javascript
// Bad: Only tests success
it('creates user', async () => {
  const user = await createUser({ email: 'test@example.com' });
  expect(user.id).toBeDefined();
});

// Good: Tests edge cases and errors
it('rejects duplicate email', async () => {
  await createUser({ email: 'test@example.com' });
  await expect(createUser({ email: 'test@example.com' }))
    .rejects.toThrow('Email already exists');
});

it('rejects invalid email format', async () => {
  await expect(createUser({ email: 'not-an-email' }))
    .rejects.toThrow('Invalid email');
});
```

## CI/CD Integration

### Playwright

```yaml
# .github/workflows/test.yml
- name: Install Playwright
  run: npx playwright install --with-deps

- name: Run E2E tests
  run: npx playwright test --shard=${{ matrix.shard }}/${{ strategy.job-total }}
  
- name: Upload trace
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-trace
    path: test-results/
```

**Use sharding for parallel execution: `--shard=1/4` splits suite into 4 parts.**

### Cypress

```yaml
- name: Cypress run
  uses: cypress-io/github-action@v5
  with:
    start: npm start
    wait-on: 'http://localhost:3000'
    record: true
  env:
    CYPRESS_RECORD_KEY: ${{ secrets.CYPRESS_RECORD_KEY }}
```

### Jest

```yaml
- name: Run unit tests
  run: npm test -- --coverage --maxWorkers=2
```

## Pre-Flight Validation Checklist

Before merging test code:

- [ ] Tests pass locally and in CI
- [ ] No hardcoded waits (`sleep`, `wait(5000)`)—use explicit waits for conditions
- [ ] Selectors are semantic (role-based or label-based, not CSS classes)
- [ ] Each test is independent (can run in any order)
- [ ] Mocks are at module boundaries, not internal functions
- [ ] Error cases and edge cases are tested, not just happy paths
- [ ] Test names describe behavior, not implementation ("displays error when email is invalid" not "calls validateEmail")
- [ ] No commented-out assertions or skipped tests without a tracked issue

## When Tests Fail

1. **Read the error message.** Playwright and Jest provide detailed failure output.
2. **Check if it's flaky.** Run the test 10 times locally. If it passes sometimes, it's a timing issue.
3. **Use debugging tools.** Playwright trace viewer, Cypress time-travel, Jest's `--watch` mode.
4. **Reproduce locally.** If it only fails in CI, check for environment differences (ports, data, timing).
5. **Quarantine if necessary.** If a test is flaky and you can't fix it immediately, skip it with a tracked issue. Don't let it poison the suite.

## Maintenance Strategy

**Tests are code.** They need refactoring, DRY principles, and clear naming just like production code.

**Delete obsolete tests.** If a feature is removed, delete its tests. If a test hasn't failed in 6 months and covers a trivial path, consider deleting it.

**Refactor when you notice duplication.** Extract setup logic into fixtures, helpers, or custom commands.

**Review test failures in aggregate.** If the same selector breaks across 20 tests, that's a sign to use a more stable locator or create a shared helper.

## Final Notes

You're not aiming for perfect tests. You're aiming for tests that catch real bugs, run fast, and don't break on every refactor. Prioritize critical user journeys. Test edge cases that have actually caused production issues. Ignore trivial paths.

When in doubt: **Would this test have caught a bug that reached production?** If no, reconsider writing it.