#!/bin/bash
# Run migration using psql directly with Supabase connection string

# Read .env file
export $(cat .env | grep -v '^#' | xargs)

# Supabase connection details
PROJECT_REF="jzinycxsxveexsghzcob"
DB_HOST="db.${PROJECT_REF}.supabase.co"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"

echo "============================================================"
echo "PersonaChat V1 Database Migration"
echo "============================================================"
echo ""
echo "This will execute the migration SQL against your Supabase database."
echo "Project: ${PROJECT_REF}"
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo "Error: psql is not installed."
    echo "Install it with: brew install libpq"
    echo "Then add to PATH: export PATH=\"/opt/homebrew/opt/libpq/bin:\$PATH\""
    exit 1
fi

# Prompt for database password
echo "Enter your Supabase database password:"
echo "(Find it in: https://supabase.com/dashboard/project/${PROJECT_REF}/settings/database)"
read -s DB_PASSWORD
echo ""

# Build connection string
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f migrate_to_v1.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✓ Migration completed successfully!"
    echo "============================================================"
    echo ""
    echo "Your database has been upgraded to V1 schema."
    echo "Old conversations backed up to 'conversations_backup_old'."
    echo ""
    echo "You can now restart the application and test the features."
else
    echo ""
    echo "============================================================"
    echo "✗ Migration failed"
    echo "============================================================"
    echo ""
    echo "Please check the error messages above."
    echo "You may need to run the SQL manually in the Supabase dashboard:"
    echo "https://supabase.com/dashboard/project/${PROJECT_REF}/sql"
fi
