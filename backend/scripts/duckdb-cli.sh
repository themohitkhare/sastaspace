#!/bin/bash
# Helper script to access DuckDB CLI with the project database

# Get the script directory and resolve relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DB_PATH="${DB_PATH:-$PROJECT_ROOT/backend/data/sastaspace.db}"

# Create database directory if it doesn't exist
mkdir -p "$(dirname "$DB_PATH")"

# Run DuckDB CLI with the database file
# Use -ui flag for web UI if available, otherwise interactive mode
if command -v duckdb &> /dev/null; then
    # Check if database file exists and is readable, or create it
    if [ ! -f "$DB_PATH" ] || [ -r "$DB_PATH" ]; then
        # If no arguments provided and file doesn't exist, DuckDB will create it
        duckdb "$DB_PATH" "$@"
    else
        echo "Error: Cannot access database file $DB_PATH"
        echo "The file exists but you don't have permission to read it."
        echo "Try: sudo chown $USER:$USER $DB_PATH"
        exit 1
    fi
else
    echo "Error: DuckDB CLI not found. Please install DuckDB."
    if [ -f "/home/mkhare/.local/bin/duckdb" ]; then
        echo "DuckDB is installed at: /home/mkhare/.local/bin/duckdb"
        echo "Make sure /home/mkhare/.local/bin is in your PATH"
    fi
    exit 1
fi
