# Security Review Checklist

> Read by: arms-security-agent
> Triggered by: `run review`, any auth/RLS/token-related task

---

## Authentication & Authorization

### Auth Flow Validation
```
[ ] Auth tokens are never stored in localStorage — use httpOnly cookies or Supabase session management
[ ] JWT expiry is configured (default Supabase: 1 hour access, 7 day refresh)
[ ] Refresh token rotation is enabled in Supabase Auth settings
[ ] Password reset flows use time-limited tokens
[ ] OAuth redirect URIs are whitelisted — no open redirects
[ ] Sign-out invalidates session server-side, not just client-side
```

### Route Protection
```
[ ] All authenticated routes check session server-side (middleware or getServerSideProps)
[ ] API routes validate auth before processing — never trust client-supplied user IDs
[ ] Admin routes have role check, not just auth check
[ ] Public routes do not leak private data in response
```

---

## Supabase RLS Policy Review

For every table, verify:

```
[ ] RLS is ENABLED — `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY`
[ ] At minimum: SELECT, INSERT, UPDATE, DELETE policies defined or explicitly denied
[ ] Policies use auth.uid() — never trust user-supplied IDs
[ ] No policy uses `USING (true)` on sensitive tables — this is public read
[ ] Service role key is server-side only — never in client bundle
```

### Common RLS Patterns

**User owns their own rows:**
```sql
CREATE POLICY "owner_select" ON table_name
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "owner_insert" ON table_name
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "owner_update" ON table_name
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "owner_delete" ON table_name
  FOR DELETE USING (auth.uid() = user_id);
```

**Admin-only table:**
```sql
CREATE POLICY "admin_only" ON table_name
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM user_roles
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );
```

**Red flags to block:**
- `USING (true)` on any non-public table
- Policies that reference user input directly without `auth.uid()`
- Tables with no RLS policies at all
- `service_role` key referenced anywhere client-side

---

## OWASP Top 10 — ARMS Stack Mapping

| Risk | Where to Check | Mitigation |
|---|---|---|
| Injection | API routes, DB queries | Use Supabase client (parameterized), never string-concat SQL |
| Broken Auth | Auth flows, session handling | Validate server-side, rotate tokens, httpOnly cookies |
| Sensitive Data Exposure | API responses, logs | Never log tokens/passwords, strip sensitive fields from responses |
| Security Misconfiguration | `.env`, RLS policies, CORS | Review env vars, enforce RLS, restrict CORS origins |
| XSS | User-generated content, dangerouslySetInnerHTML | Sanitize all user input, avoid raw HTML injection in React |
| Insecure Dependencies | `package.json` | Run `npm audit`, flag high/critical CVEs |
| Broken Access Control | Route guards, API auth | Server-side auth checks on every protected endpoint |
| CSRF | Form submissions, API mutations | Use SameSite cookies, validate origin headers |
| Logging Failures | Error handlers | Log errors without sensitive data, monitor for anomalies |
| SSRF | External API calls | Validate/whitelist outbound URLs, never forward user-supplied URLs |

---

## API Security

```
[ ] All mutation endpoints (POST/PUT/PATCH/DELETE) require authentication
[ ] Rate limiting configured on auth endpoints (login, signup, password reset)
[ ] CORS origin restricted — not wildcard (*) in production
[ ] API responses do not include stack traces in production
[ ] File upload endpoints validate type, size, and sanitize filename
[ ] Webhooks validate signature before processing
```

---

## Client-Side Security

```
[ ] No secrets in client bundle — run `NEXT_PUBLIC_` audit
[ ] No `dangerouslySetInnerHTML` without sanitization (use DOMPurify)
[ ] Content Security Policy headers configured
[ ] No sensitive data in browser localStorage (tokens, PII)
[ ] Third-party scripts loaded with `integrity` attribute where possible
```

**Audit client bundle for secrets:**
```bash
grep -r "SUPABASE_SERVICE_ROLE" .next/
grep -r "SECRET" .next/static/
```
Any match = critical violation → block deploy, escalate to arms-main-agent → **HALT**

---

## Dependency Audit

Run before every deploy:
```bash
npm audit --audit-level=high
```

| Severity | Action |
|---|---|
| Critical | Block deploy, fix immediately |
| High | Fix before deploy or get explicit user approval to defer |
| Moderate | Log in SESSION.md, schedule fix |
| Low | Log, no block |

---

## Pre-Deploy Security Sign-Off

arms-security-agent must confirm before `run deploy` proceeds:

```
[ ] RLS policies reviewed on all tables modified in this release
[ ] No secrets in client bundle
[ ] npm audit — zero critical/high (or deferred with approval)
[ ] Auth flows validated
[ ] CORS configured correctly for production domain
```

If any item fails → block deploy → report to arms-main-agent → **HALT**
