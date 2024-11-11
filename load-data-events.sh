#!/bin/bash

set -euo pipefail

# Set variables
CSV_FILE="events.csv"
DATABASE_FILE="events.db"

# Start a new SQLite database and execute commands
sqlite3 "$DATABASE_FILE" <<EOF
-- Turn off synchronous mode for faster inserts
PRAGMA synchronous = OFF;
-- Use memory journal mode for faster inserts
PRAGMA journal_mode = MEMORY;

-- Create the taxonomy table
CREATE TABLE taxonomy (
    event_name TEXT,
    version TEXT,
    tax_id INTEGER,
    parent_id INTEGER,
    rank TEXT,
    name TEXT
);

-- Import data directly from CSV
.mode csv
.import $CSV_FILE taxonomy

-- Create the requested indices after data import
CREATE INDEX idx_tax_id ON taxonomy (tax_id);
CREATE INDEX idx_tax_id_version ON taxonomy (tax_id, version);

-- Restore the synchronous and journal mode settings to default
PRAGMA synchronous = FULL;
PRAGMA journal_mode = DELETE;
EOF

echo "Data imported and indices created successfully."
