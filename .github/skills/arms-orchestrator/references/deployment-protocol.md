# Deployment Protocol

> Read by: arms-devops-agent
> Triggered by: `run deploy`, `run pipeline`

ARMS enforces a strict deployment sequence. Cloud-first deployment is not supported — all changes must pass local validation before any remote push.

---

## Pre-Deployment Checklist (Mandatory)

arms-devops-agent must confirm all items before proceeding:

```
[ ] supabase db reset — local migrations clean
[ ] supabase gen types typescript — types in sync
[ ] npm run build — zero errors
[ ] npm run lint — zero warnings
[ ] npm run type-check — strict mode passing
[ ] npm run test — all tests passing (or explicitly deferred with user approval)
[ ] arms-security-agent sign-off — RLS policies reviewed
[ ] Git checkpoint committed — chore: pre-deploy checkpoint
```

If any item fails → surface blocker to arms-main-agent → **HALT**

---

## Environment Variable Management

### Local Development
- Store in `.env.local` (never commit)
- Template in `.env.example` (always commit, no real values)

### Production
- Vercel: set via dashboard or `vercel env add`
- Docker/VPS: inject at runtime via CI secrets or `.env.production` (excluded from git)
- AWS/GCP: use Secrets Manager / Secret Manager

### Required Variables (Next.js + Supabase)
```bash
# .env.example
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=       # server-side only, never expose to client
NEXT_PUBLIC_APP_URL=
```

**Rule:** `SUPABASE_SERVICE_ROLE_KEY` must never appear in client-side bundles. arms-security-agent validates this during review.

---

## Deployment Targets

### [1] Vercel

```bash
# First deploy
vercel --prod

# Subsequent deploys (via git)
git push origin main  # auto-deploys if Vercel connected to repo

# Manual production deploy
vercel --prod --force
```

**Environment setup:**
```bash
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel env add SUPABASE_SERVICE_ROLE_KEY production
```

**Post-deploy:**
- Verify deployment URL is live
- Check Vercel function logs for runtime errors
- Confirm environment variables loaded correctly

### [2] Docker / VPS

```dockerfile
# Dockerfile (Next.js)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

```bash
# Build and run
docker build -t arms-app .
docker run -p 3000:3000 --env-file .env.production arms-app
```

**VPS deploy steps:**
1. SSH into server
2. `git pull origin main`
3. `docker build -t arms-app .`
4. `docker stop arms-app-container || true`
5. `docker run -d --name arms-app-container -p 3000:3000 --env-file .env.production arms-app`

### [3] AWS / GCP

Delegate to infrastructure-specific CI/CD. arms-devops-agent generates the pipeline config. Request user approval before applying infrastructure changes → **HALT**

---

## Supabase Cloud Deployment

```bash
# Push migrations to remote (only after local validation)
supabase db push

# Verify remote schema matches local
supabase db diff --linked
```

**Order:**
1. Deploy DB migrations first (`supabase db push`)
2. Deploy application second
3. Never deploy app before DB schema is in sync — type mismatches will cause runtime errors

---

## Staging vs Production

| Environment | Branch | Deploy Trigger | Approval |
|---|---|---|---|
| Local | — | Manual | None |
| Staging | `develop` | Auto on PR merge | QA sign-off |
| Production | `main` | Manual only | Explicit user HALT |

**Never auto-deploy to production.** All production deploys require explicit user approval → **HALT**

---

## Release Notes

arms-devops-agent generates release notes from git log before every production deploy:

```bash
git log --oneline <last-tag>..HEAD
```

Format:
```markdown
## Release vX.Y.Z — <date>

### Features
- feat(auth): add OAuth login flow

### Fixes
- fix(db): correct RLS policy on profiles table

### Chores
- chore(deps): upgrade Next.js to 15.x
```

Present to user for review → **HALT**

---

## Post-Deploy Verification

```bash
# Check deployment health
curl -f https://<your-domain>/api/health || echo "Health check failed"

# Verify Supabase connection
curl https://<your-domain>/api/db-status
```

If health check fails → rollback immediately (see `error-recovery-playbook.md`)
