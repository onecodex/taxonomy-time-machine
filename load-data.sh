#!/bin/bash

set -euo pipefail

# Set variables
CSV_FILE="taxonomy-data.csv"
DATABASE_FILE="taxonomy.db"

TEMP_CSV="temp_data.csv"

# Remove the header row and create a temporary CSV without headers
tail -n +2 "$CSV_FILE" > "$TEMP_CSV"

# Start a new SQLite database and execute commands
sqlite3 "$DATABASE_FILE" <<EOF
-- Turn off synchronous mode for faster inserts
PRAGMA synchronous = OFF;
-- Use memory journal mode for faster inserts
PRAGMA journal_mode = MEMORY;

-- Create the taxonomy table
CREATE TABLE IF NOT EXISTS taxonomy (
    tax_id INTEGER,
    parent_id INTEGER,
    version INTEGER,
    name TEXT,
    rank TEXT
);

-- Import data directly from CSV
.mode csv
.import $TEMP_CSV taxonomy

-- Create the requested indices after data import
CREATE INDEX idx_tax_id ON taxonomy (tax_id);
CREATE INDEX idx_tax_id_version ON taxonomy (tax_id, version);

-- Restore the synchronous and journal mode settings to default
PRAGMA synchronous = FULL;
PRAGMA journal_mode = DELETE;
EOF

echo "Data imported and indices created successfully."
