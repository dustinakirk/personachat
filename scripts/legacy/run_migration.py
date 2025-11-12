#!/usr/bin/env python3
"""
Migration helper for PersonaChat V1 database schema.

Since Supabase Python client doesn't support direct SQL execution,
this script provides instructions for manual migration.
"""

import webbrowser

SUPABASE_PROJECT_REF = "jzinycxsxveexsghzcob"
SQL_EDITOR_URL = f"https://supabase.com/dashboard/project/{SUPABASE_PROJECT_REF}/sql"
MIGRATION_FILE = "migrate_to_v1.sql"

print("=" * 70)
print("PersonaChat V1 Database Migration")
print("=" * 70)
print()
print("To migrate your database to V1 schema, follow these steps:")
print()
print("1. Open Supabase SQL Editor in your browser:")
print(f"   {SQL_EDITOR_URL}")
print()
print("2. Copy the contents of this file:")
print(f"   {MIGRATION_FILE}")
print()
print("3. Paste the SQL into the Supabase SQL Editor")
print()
print("4. Click 'Run' to execute the migration")
print()
print("=" * 70)
print()

# Read and display first few lines of migration
with open(MIGRATION_FILE, "r") as f:
    lines = f.readlines()
    print("Migration preview (first 20 lines):")
    print("-" * 70)
    for i, line in enumerate(lines[:20], 1):
        print(f"{i:3}: {line}", end="")
    print("-" * 70)
    print(f"... and {len(lines) - 20} more lines")
    print()

response = input("Open Supabase SQL Editor in browser? (y/n): ")
if response.lower() == "y":
    webbrowser.open(SQL_EDITOR_URL)
    print("✓ Browser opened. Please copy migrate_to_v1.sql contents and run in SQL Editor.")
else:
    print("✓ Remember to run the migration manually when ready.")
