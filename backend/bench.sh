#!/bin/bash

set -euo pipefail


# this should be expressed in terms of total ingested tax IDs which is the same
# as the number of unique tax IDs in each db
for i in 1 2 5 10 20 50; do
    echo "--- creating changelog with ${i} archives"

    ./taxonomy_time_machine/load_data.py \
        --n-dumps "${i}" \
        --always-insert \
        --db-path "archive-${i}-full.db"

    ./taxonomy_time_machine/load_data.py \
        --n-dumps "${i}" \
        --db-path "archive-${i}-deduplicated.db"
done
