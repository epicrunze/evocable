#!/bin/bash
set -e

# Get environment variables or use defaults
TEXT_DATA_PATH="${TEXT_DATA_PATH:-/data/text}"
WAV_DATA_PATH="${WAV_DATA_PATH:-/data/wav}"
SEGMENT_DATA_PATH="${SEGMENT_DATA_PATH:-/data/ogg}"
META_DATA_PATH="${META_DATA_PATH:-/data/meta}"

# Validate required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is required but not set."
    echo "Please ensure DATABASE_URL is defined in your .env file or environment configuration."
    exit 1
fi

# Extract database directory from DATABASE_URL if file-based
if [[ "$DATABASE_URL" == sqlite:///* ]] && [[ "$DATABASE_URL" != *":memory:" ]]; then
    DB_FILE="${DATABASE_URL#sqlite:///}"
    DB_DIR="$(dirname "$DB_FILE")"
    # Ensure database directory exists
    mkdir -p "$DB_DIR"
fi

# Create directories if they don't exist
mkdir -p "$META_DATA_PATH" "$TEXT_DATA_PATH" "$WAV_DATA_PATH" "$SEGMENT_DATA_PATH"

# Ensure the directories have proper permissions (readable/writable)
chmod -R 755 "$META_DATA_PATH" "$TEXT_DATA_PATH" "$WAV_DATA_PATH" "$SEGMENT_DATA_PATH" 2>/dev/null || true

# Create the database file if it doesn't exist and set permissions
if [[ "$DATABASE_URL" == sqlite:///* ]] && [[ "$DATABASE_URL" != *":memory:" ]]; then
    if [ ! -f "$DB_FILE" ]; then
        touch "$DB_FILE"
        chmod 666 "$DB_FILE"
    fi
fi

# Ensure app user owns all data directories
ALL_PATHS="$META_DATA_PATH $TEXT_DATA_PATH $WAV_DATA_PATH $SEGMENT_DATA_PATH"
if [[ "$DATABASE_URL" == sqlite:///* ]] && [[ "$DATABASE_URL" != *":memory:" ]]; then
    ALL_PATHS="$ALL_PATHS $DB_DIR"
fi
for path in $ALL_PATHS; do
    chown -R app:app "$path" 2>/dev/null || true
done

# Switch to app user and run the main application
exec gosu app "$@" 