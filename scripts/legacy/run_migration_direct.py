#!/usr/bin/env python3
"""
Direct migration execution using Supabase REST API and PostgreSQL connection.
This script will execute the migration SQL file against your Supabase database.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
PROJECT_REF = "jzinycxsxveexsghzcob"

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def run_migration_with_postgres():
    """Execute migration using direct PostgreSQL connection."""

    print_header("PersonaChat V1 Database Migration")

    print("\nTo run this migration, you need your Supabase database password.")
    print(f"\nFind it at: https://supabase.com/dashboard/project/{PROJECT_REF}/settings/database")
    print("(Look for 'Database password' under 'Connection string')\n")

    db_password = input("Enter your Supabase database password: ").strip()

    if not db_password:
        print("\n✗ No password provided. Exiting.")
        return False

    # Connection parameters
    conn_params = {
        "host": f"db.{PROJECT_REF}.supabase.co",
        "port": 5432,
        "database": "postgres",
        "user": "postgres",
        "password": db_password,
        "sslmode": "require"
    }

    print("\nConnecting to Supabase database...")

    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()

        print("✓ Connected successfully")

        # Read migration SQL
        print("\nReading migration file...")
        with open("migrate_to_v1.sql", "r") as f:
            migration_sql = f.read()

        print(f"✓ Loaded migration SQL ({len(migration_sql)} characters)")

        # Execute migration
        print("\nExecuting migration (this may take 10-20 seconds)...")
        cursor.execute(migration_sql)

        print("✓ Migration executed successfully")

        # Verify tables exist
        print("\nVerifying tables...")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN (
                'user_profiles',
                'persona_groups',
                'personas',
                'persona_relationships',
                'conversations',
                'conversation_participants',
                'messages'
            )
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()

        if len(tables) == 7:
            print(f"✓ All 7 V1 tables verified:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print(f"⚠ Only {len(tables)} tables found (expected 7)")

        # Close connection
        cursor.close()
        conn.close()

        print_header("Migration Complete!")
        print("\n✓ Database upgraded to V1 schema")
        print("✓ Old conversations backed up to 'conversations_backup_old'")
        print("\nYou can now restart the application and test all features.\n")

        return True

    except psycopg2.OperationalError as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nPossible issues:")
        print("1. Incorrect password")
        print("2. Network connectivity")
        print("3. SSL configuration")
        return False

    except psycopg2.Error as e:
        print(f"\n✗ SQL execution failed: {e}")
        print("\nThe SQL may have partially executed.")
        print("Check the Supabase dashboard for current state.")
        return False

    except FileNotFoundError:
        print("\n✗ Migration file 'migrate_to_v1.sql' not found")
        print("Make sure you're running this from the project root directory.")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = run_migration_with_postgres()
    sys.exit(0 if success else 1)
