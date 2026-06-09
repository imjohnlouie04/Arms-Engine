---
name: security-code-review
description: >
  Perform security-focused code reviews following OWASP best practices. Use this for code review requests, security audits, vulnerability assessments, pull request reviews, or whenever code is shared for feedback. Covers injection flaws, authentication issues, XSS, CSRF, insecure dependencies, cryptographic failures, access control problems, security misconfigurations, and other OWASP Top 10 vulnerabilities. Applies to any programming language including JavaScript, Python, Java, C#, PHP, Go, Ruby, and others.
---

# Security Code Review

Review code through a security lens, identifying vulnerabilities and suggesting concrete fixes based on OWASP principles.

## Review Process

1. **Understand context** — Ask about the application type (web app, API, mobile backend, etc.) and tech stack if not obvious
2. **Scan for OWASP Top 10 patterns** — Focus on the most critical vulnerability classes
3. **Identify issues** — Note severity (Critical, High, Medium, Low)
4. **Provide fixes** — Show concrete code improvements, not just descriptions
5. **Explain why** — Help developers understand the attack vector and impact

## Critical Vulnerability Patterns

### Injection Flaws

SQL, NoSQL, OS command, LDAP, or expression language injection occurs when untrusted data is sent to an interpreter.

**Red flags:**
- String concatenation in queries: `"SELECT * FROM users WHERE id = " + userId`
- Shell commands with user input: `exec("rm " + filename)`
- Unparameterized database queries
- `eval()` or equivalent with user-controlled data

**Fix pattern:** Use parameterized queries, prepared statements, ORMs with proper escaping, or input validation with strict allowlists.

```python
# Vulnerable
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

# Fixed
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

### Authentication & Session Issues

**Red flags:**
- Passwords stored in plaintext or with weak hashing (MD5, SHA1)
- Missing rate limiting on login endpoints
- Predictable session tokens or tokens in URLs
- No session expiration or logout functionality
- Missing multi-factor authentication for sensitive operations

**Fix pattern:** Use bcrypt/argon2 for passwords, implement exponential backoff on failed attempts, use cryptographically secure session tokens (httpOnly, secure, sameSite cookies), enforce timeouts.

### Cross-Site Scripting (XSS)

Occurs when user input is rendered in HTML without proper escaping.

**Red flags:**
- `innerHTML = userInput` or equivalent
- Direct rendering of user content in templates without escaping
- Unsafe use of `dangerouslySetInnerHTML` in React
- User data in JavaScript contexts without encoding

**Fix pattern:** Use framework auto-escaping (React JSX, Vue templates, Django templates with autoescaping on), DOMPurify for rich content, Content Security Policy headers.

```javascript
// Vulnerable
div.innerHTML = userComment;

// Fixed
div.textContent = userComment; // or use framework escaping
```

### Broken Access Control

**Red flags:**
- Missing authorization checks (only authentication)
- Insecure direct object references: `/api/user/123/profile` without verifying ownership
- Elevation of privilege: Regular users accessing admin endpoints
- CORS misconfiguration: `Access-Control-Allow-Origin: *` with credentials

**Fix pattern:** Implement resource-level authorization checks. Verify the authenticated user owns or has permission for the requested resource.

```python
# Vulnerable
@app.route('/document/<doc_id>')
def get_document(doc_id):
    return Document.query.get(doc_id)

# Fixed
@app.route('/document/<doc_id>')
@login_required
def get_document(doc_id):
    doc = Document.query.get(doc_id)
    if doc.owner_id != current_user.id:
        abort(403)
    return doc
```

### Cryptographic Failures

**Red flags:**
- Sensitive data transmitted over HTTP
- Hardcoded secrets, API keys, or passwords in code
- Weak encryption algorithms (DES, RC4)
- Custom crypto implementations
- Unencrypted sensitive data at rest

**Fix pattern:** Use TLS 1.2+, store secrets in environment variables or secret managers, use vetted libraries (libsodium, NaCl), encrypt PII and financial data.

### Security Misconfiguration

**Red flags:**
- Debug mode enabled in production
- Default credentials still active
- Verbose error messages exposing stack traces
- Unnecessary services or ports exposed
- Missing security headers (HSTS, X-Frame-Options, X-Content-Type-Options)

**Fix pattern:** Harden production configs, disable debug/verbose errors, implement security headers, principle of least privilege for service accounts.

### Vulnerable Dependencies

**Red flags:**
- Outdated packages with known CVEs
- No dependency scanning in CI/CD
- Unused dependencies increasing attack surface

**Fix pattern:** Regularly run `npm audit`, `pip-audit`, Snyk, or Dependabot. Pin versions and update systematically.

### Insecure Deserialization

**Red flags:**
- Deserializing untrusted data with `pickle`, `yaml.load`, Java serialization
- No integrity checks on serialized objects

**Fix pattern:** Avoid deserializing untrusted data. Use JSON or implement HMAC signatures to verify integrity.

### Server-Side Request Forgery (SSRF)

**Red flags:**
- Fetching URLs provided by users without validation
- No allowlist for external API calls
- Internal network access from user-controlled input

**Fix pattern:** Validate and allowlist URLs, block private IP ranges, use separate network segments.

### Logging & Monitoring Gaps

**Red flags:**
- No logging of authentication events
- Sensitive data (passwords, tokens) in logs
- No alerting on suspicious patterns

**Fix pattern:** Log security events (login, logout, failures, privilege changes), redact sensitive data, implement anomaly detection.

## Language-Specific Patterns

### JavaScript/TypeScript
- Prototype pollution: Validate object keys before assignment
- ReDoS: Avoid complex regex on user input without timeouts
- `eval()`, `Function()`, `setTimeout(string)`: Never use with user input

### Python
- `pickle.loads()`: Never on untrusted data
- `yaml.load()`: Use `yaml.safe_load()`
- SQL: Use parameterized queries or SQLAlchemy ORM

### Java
- `Runtime.exec()`: Validate input strictly
- XML External Entities (XXE): Disable external entity processing
- Deserialization: Avoid or use allowlists

### PHP
- `eval()`, `assert()`: Never with user input
- File inclusion: Validate paths, use allowlists
- Type juggling: Use strict comparison (`===`)

## Review Output Format

Structure findings clearly:

**Critical Issues** (immediate exploitation risk)
- Describe the vulnerability
- Show vulnerable code snippet
- Explain the attack scenario
- Provide fixed code

**High Priority** (significant risk under certain conditions)
**Medium Priority** (defense-in-depth improvements)
**Low Priority** (best practice suggestions)

**Positive observations** — Note what's done well to reinforce good practices.

## Example Review

**Code submitted:**
```javascript
app.post('/login', (req, res) => {
  const { username, password } = req.body;
  db.query(`SELECT * FROM users WHERE username='${username}' AND password='${password}'`, (err, results) => {
    if (results.length > 0) {
      req.session.user = results[0];
      res.json({ success: true });
    }
  });
});
```

**Review:**

🔴 **Critical: SQL Injection**
The query uses string interpolation with user input, allowing attackers to inject SQL. An attacker could use `username = admin' --` to bypass authentication.

```javascript
// Fixed
app.post('/login', (req, res) => {
  const { username, password } = req.body;
  db.query('SELECT * FROM users WHERE username = ? AND password = ?', 
    [username, password], (err, results) => {
    // ... rest of logic
  });
});
```

🔴 **Critical: Plaintext Password Storage**
Passwords appear to be stored in plaintext. Use bcrypt or argon2.

```javascript
const bcrypt = require('bcrypt');

// On registration
const hashedPassword = await bcrypt.hash(password, 12);

// On login
const match = await bcrypt.compare(password, user.password_hash);
```

🟡 **High: No Rate Limiting**
Implement rate limiting to prevent brute force attacks:

```javascript
const rateLimit = require('express-rate-limit');
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5
});
app.post('/login', loginLimiter, (req, res) => { ... });
```

🟡 **High: Session Fixation Risk**
Regenerate session ID after authentication:

```javascript
req.session.regenerate((err) => {
  req.session.user = results[0];
  res.json({ success: true });
});
```

## When to Escalate

Some issues require specialist review:
- Custom cryptographic implementations
- Payment processing logic
- Complex authorization systems
- Native code or memory management

Recommend security audit or penetration testing for high-risk applications handling sensitive data.

## Additional Considerations

- **Context matters**: A vulnerability's severity depends on data sensitivity and exposure
- **Defense in depth**: Multiple layers reduce risk even if one fails
- **Usability vs security**: Find pragmatic balances; don't make systems unusable
- **Threat modeling**: Consider the application's specific threat landscape

Provide actionable, educational reviews that improve both the code and the developer's security awareness.