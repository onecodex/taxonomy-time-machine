#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
from tqdm import tqdm
import taxonomy
from datetime import datetime

from dataclasses import dataclass
from enum import Enum

import sqlite3

# iterate over tax_id, parent_id, name, rank


def dump_path_to_datetime(dump_path: Path):
    return datetime.strptime(dump_path.name.split("_")[1], "%Y-%m-%d")


taxdumps = sorted(
    [p for p in Path("dumps").glob("*") if p.is_dir()],
    key=dump_path_to_datetime,
)

# tax_id -> node dict
last_version: dict[int, dict] = {}


class EventName(Enum):
    Create = "create"
    Delete = "delete"
    Merge = "merge"
    Alter = "alter"


@dataclass
class Event:
    event_name: EventName
    id: int | None = None
    parent_id: int | None = None
    name: str | None = None
    rank: str | None = None


n_events = 0
tax_id_to_node: dict = {}
data_to_insert = []
last_tax_ids: None | set[str] = None

for n, taxdump in enumerate(taxdumps):
    taxdump_date = dump_path_to_datetime(taxdump)
    tax = taxonomy.Taxonomy.from_ncbi(str(taxdump))

    # we infer deleted nodes by comparing the tax IDs in the current dump to those
    # found in the previous dump
    seen_tax_ids: set[str] = set()
    event_counts: Counter[EventName] = Counter()
    n_new_events = 0
    events: list[Event] = []

    for tax_id in tax:
        from_node = tax_id_to_node.get(tax_id)
        to_node = tax[tax_id]
        seen_tax_ids.add(tax_id)

        event = None

        if from_node is None:
            event = Event(
                event_name=EventName.Create,
                id=to_node.id,
                rank=to_node.rank,
                name=to_node.name,
                parent_id=to_node.parent,
            )
        elif (from_node.parent, from_node.rank, from_node.name) != (
            to_node.parent,
            to_node.rank,
            to_node.name,
        ):
            event = Event(
                event_name=EventName.Alter,
                id=to_node.id,
                rank=to_node.rank,
                name=to_node.name,
                parent_id=to_node.parent,
            )

        if event is not None:
            events.append(event)
            n_new_events += 1

        tax_id_to_node[tax_id] = to_node

    # find all the deleted nodes

    # append deletions
    if last_tax_ids is not None:
        for tax_id in last_tax_ids - seen_tax_ids:
            events.append(Event(event_name=EventName.Delete, id=tax_id))
    last_tax_ids = seen_tax_ids

    for event in events:
        event_counts[event.event_name] += 1
        data_to_insert.append(
            {
                "event_name": event.event_name.value,
                "version_date": taxdump_date,
                "tax_id": event.id,
                "parent_id": event.parent_id,
                "rank": event.rank,
                "name": event.name,
            }
        )
        n_events += 1

    print(f"{n}/{len(taxdumps)} total_events={n_events:,} n_new_events={n_new_events:,}")

    for event_name, count in event_counts.items():
        print(f"    {event_name.value:>20} -> {count:,}")

    print()


# Connect to the SQLite database
conn = sqlite3.connect("events.db")
cursor = conn.cursor()

# Optimized PRAGMA settings for faster inserts
cursor.execute("PRAGMA synchronous = OFF;")
cursor.execute("PRAGMA journal_mode = MEMORY;")
cursor.execute("PRAGMA temp_store = MEMORY;")


# Create the table with appropriate types
cursor.execute("""
CREATE TABLE IF NOT EXISTS taxonomy (
    event_name TEXT,
    version_date DATETIME,
    tax_id INTEGER,
    parent_id INTEGER,
    rank TEXT,
    name TEXT
)
""")

# Batch insert using transactions and executemany
batch_size = 10_000  # Insert 10,000 rows at a time

# Loop through data in batches to avoid memory overload
for i in tqdm(range(0, len(data_to_insert), batch_size)):
    batch = data_to_insert[i : i + batch_size]
    cursor.executemany(
        """
        INSERT INTO taxonomy (event_name, version_date, tax_id, parent_id, rank, name)
        VALUES (:event_name, :version_date, :tax_id, :parent_id, :rank, :name)
    """,
        batch,
    )

# Commit the transaction after all batches are processed
conn.commit()

# Create the requested indices after data import
cursor.execute("CREATE INDEX idx_tax_id ON taxonomy (tax_id);")
cursor.execute("CREATE INDEX idx_tax_id_version_date ON taxonomy (tax_id, version_date);")

# Restore the synchronous and journal mode settings to default
cursor.execute("PRAGMA synchronous = FULL;")
cursor.execute("PRAGMA journal_mode = DELETE;")

conn.close()
