# Supabase Local Development Workflow

ARMS requires local Supabase setup before any cloud deployment. This ensures schema changes are tested locally and migrations are version-controlled.

## Prerequisites

- Docker Desktop installed and running
- Node.js 20 or later
- Supabase CLI installed: `brew install supabase/tap/supabase` (macOS) or `npm install supabase --save-dev` (project-local)

## Initial Setup

### 1. Initialize Supabase

```bash
supabase init
```

Creates `supabase/` directory with:

- `config.toml` — local Supabase configuration
- `migrations/` — schema migration files
- `seed.sql` — seed data for local development

### 2. Start Local Stack

```bash
supabase start
```

Spins up Docker containers for:

- PostgreSQL database
- Supabase Studio (http://localhost:54323)
- Auth server
- Storage server
- Edge Functions runtime

First run downloads Docker images (~2-3 minutes). Subsequent starts are faster.

**Output includes:**

- API URL: `http://localhost:54321`
- DB URL: `postgresql://postgres:postgres@localhost:54322/postgres`
- Studio URL: `http://localhost:54323`
- `anon` key (for client-side)
- `service_role` key (for server-side — never expose to client)

### 3. Link to Remote Project (Optional)

Only needed if you have an existing Supabase cloud project:

```bash
supabase login
supabase link --project-ref <project-id>
```

To pull existing schema:

```bash
supabase db pull
```

Creates a migration file reflecting current remote schema.

## Daily Workflow

### Making Schema Changes

**Option A: Use Studio UI**

1. Open http://localhost:54323
2. Make changes via Table Editor
3. Capture changes:

```bash
supabase db diff -f <migration-name>
```

Example:

```bash
supabase db diff -f add_users_table
```

Creates `supabase/migrations/<timestamp>_add_users_table.sql`

**Option B: Write SQL Directly**

1. Create migration file:

```bash
supabase migration new <migration-name>
```

2. Edit the generated file in `supabase/migrations/`
3. Apply migration:

```bash
supabase db reset
```

`db reset` drops local database and reapplies all migrations from scratch. This ensures migrations are reproducible.

### Applying Migrations

**Local:**

```bash
supabase db reset
```

**Remote (after approval):**

```bash
supabase db push
```

**Never push to remote without:**

1. Testing locally with `db reset`
2. Verifying seed data still works
3. Running pre-flight QA
4. Explicit approval from user

## Row Level Security (RLS)

RLS policies must be included in migration files:

```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only read their own data
CREATE POLICY "Users can read own data"
  ON users
  FOR SELECT
  USING (auth.uid() = id);

-- Policy: Users can update their own data
CREATE POLICY "Users can update own data"
  ON users
  FOR UPDATE
  USING (auth.uid() = id);
```

**arms-security-agent must review all RLS policies before deployment.**

## Seed Data

Edit `supabase/seed.sql` for local test data:

```sql
-- Insert test users
INSERT INTO users (id, email, name)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'test@example.com', 'Test User'),
  ('00000000-0000-0000-0000-000000000002', 'admin@example.com', 'Admin User');
```

Seed data runs automatically on `supabase db reset`.

## Common Commands

| Command | Purpose |
|---|---|
| `supabase start` | Start local stack |
| `supabase stop` | Stop local stack (preserves data) |
| `supabase stop --no-backup` | Stop and delete all data |
| `supabase db reset` | Drop DB and reapply all migrations |
| `supabase db diff -f <name>` | Generate migration from Studio changes |
| `supabase migration new <name>` | Create empty migration file |
| `supabase db push` | Push migrations to remote |
| `supabase db pull` | Pull remote schema as migration |
| `supabase status` | Show running services |

## TypeScript Type Generation

Generate TypeScript types from database schema:

```bash
supabase gen types typescript --local > src/types/supabase.ts
```

Run after every schema change. Keeps frontend types in sync with database.

## Troubleshooting

### "Docker not running"

Start Docker Desktop before `supabase start`.

### "Port already in use"

Another service is using Supabase ports (54321-54324). Stop conflicting services or change ports in `supabase/config.toml`.

### "Migration failed"

1. Check migration SQL for syntax errors
2. Ensure migrations are in correct order (timestamps)
3. Run `supabase db reset` to start fresh

### "Type mismatch after schema change"

Regenerate types:

```bash
supabase gen types typescript --local > src/types/supabase.ts
```

## Best Practices

1. **Always test migrations locally** before pushing to remote
2. **Use descriptive migration names**: `add_user_profiles_table`, not `migration1`
3. **One logical change per migration**: easier to debug and rollback
4. **Include RLS policies in migrations**: security is part of schema
5. **Keep seed.sql updated**: should reflect realistic test data
6. **Run `db reset` after pulling teammate's migrations**: ensures local DB matches git
7. **Never commit `.env`**: use `.env.local` for local keys
8. **Regenerate types after every schema change**: prevents runtime errors

## Integration with ARMS Workflow

1. `arms-data-agent` proposes schema changes
2. Generate migration with `supabase db diff` or `migration new`
3. Request approval → **HALT**
4. Apply locally with `supabase db reset`
5. `arms-qa-agent` runs tests against local DB
6. `arms-security-agent` reviews RLS policies
7. Commit migration file to git
8. Only after production approval: `supabase db push`

---

**Local Supabase is mandatory for ARMS projects. Cloud-first development is not supported.**