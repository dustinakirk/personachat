# Legacy Migration Scripts

These scripts were used for manual database migrations before the automated CI/CD workflow was implemented.

## Files

- **run_migration.py** - Opens browser to Supabase SQL Editor (manual copy/paste)
- **run_migration_direct.py** - Direct PostgreSQL connection via psycopg2
- **run_migration_psql.sh** - Bash script using psql CLI

## Current Migration Workflow

The project now uses **automated migrations via GitHub Actions**:

1. Edit/create migration files in `supabase/migrations/`
2. Commit and push to main branch
3. GitHub Actions automatically applies migrations
4. View status in Actions tab

See the main README.md for details on the automated workflow.

## When to Use These Scripts

These legacy scripts can still be used as a **manual fallback** if:
- GitHub Actions is unavailable
- You need to test migrations locally before committing
- Emergency database changes are needed

### Usage

```bash
# Option 1: Direct Python execution (requires database password)
python scripts/legacy/run_migration_direct.py

# Option 2: Using psql (requires database password)
bash scripts/legacy/run_migration_psql.sh

# Option 3: Manual browser (opens Supabase dashboard)
python scripts/legacy/run_migration.py
```

**Note:** The original `migrate_to_v1.sql` file has been moved to `supabase/migrations/20251111000000_v1_migration.sql` and is managed by the Supabase CLI.
