#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
from tqdm import tqdm
import taxonomy
from datetime import datetime

from dataclasses import dataclass
from enum import Enum

from typing import Literal, TypedDict
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
    Alter = "alter"
    Merge = "merge"


@dataclass
class Event:
    event_name: EventName
    id: int
    parent_id: int | None
    name: str | None
    rank: str | None


class Row(TypedDict):
    event_name: Literal["create", "delete", "alter", "merge"]
    version_date: str
    tax_id: int
    parent_id: int | None
    name: str | None
    rank: str | None


n_events = 0
total_seen_taxa = 0

tax_id_to_node: dict = {}
data_to_insert: list[Row] = []
last_tax_ids: None | set[str] = None

# `merged.dmp` is appended to with each version; so we need to
# only record *new* entries in merged.dmp. This set lets us track
# that easily
seen_merged_tax_ids: set[int] = set()

taxdumps = taxdumps[::20]


for n, taxdump in enumerate(taxdumps):
    taxdump_date = dump_path_to_datetime(taxdump)
    tax = taxonomy.Taxonomy.from_ncbi(str(taxdump))
    print(f"--- loaded {taxdump}: {tax}")

    total_seen_taxa += len(tax)

    # we infer deleted nodes by comparing the tax IDs in the current dump to those
    # found in the previous dump
    seen_tax_ids: set[str] = set()
    event_counts: Counter[EventName] = Counter()
    n_new_events = 0
    events: list[Event] = []

    last_merged_tax_ids = set[str]

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

    # find deleted nodes by looking for tax_ids dropped since the last build
    if last_tax_ids is not None:
        for tax_id in last_tax_ids - seen_tax_ids:
            events.append(
                Event(event_name=EventName.Delete, id=tax_id, parent_id=None, name=None, rank=None)
            )
    last_tax_ids = seen_tax_ids

    # append merges (merge.dmp is an appended log so we actually only care
    # about *new* merges)
    with open(taxdump / "merged.dmp") as handle:
        for line in handle:
            parts = line.strip().split("\t")
            tax_id_1 = int(parts[0])
            tax_id_2 = int(parts[2])

            if tax_id_1 not in seen_merged_tax_ids:
                # We just pretend tax_id_2 becomes a
                # child of tax_id_1 when mergers happen
                events.append(
                    Event(
                        event_name=EventName.Merge,
                        id=tax_id_2,  # *2* is the *child*
                        parent_id=tax_id_1,
                        name=None,
                        rank=None,
                    )
                )

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
        print(f"    {event_name.value:>10} -> {count:,}")

    print()

print(f"--- {total_seen_taxa=:,}")
print(f"--- {len(data_to_insert)=:,}")
print(f"--- savings={1 - (len(data_to_insert) / total_seen_taxa):.2%}")


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

batch_size = 10_000

# Loop through data in batches to avoid memory overload
# Batch insert using transactions and executemany
for i in tqdm(range(0, len(data_to_insert), batch_size)):
    batch = data_to_insert[i : i + batch_size]
    cursor.executemany(
        """
        INSERT INTO taxonomy (event_name, version_date, tax_id, parent_id, rank, name)
        VALUES (:event_name, :version_date, :tax_id, :parent_id, :rank, :name)
    """,
        batch,
    )

conn.commit()

print("--- creating b-tree indexes")
cursor.execute("CREATE INDEX idx_tax_id ON taxonomy (tax_id);")
cursor.execute("CREATE INDEX idx_parent_id ON taxonomy (parent_id);")

# index the lowercase of `name` to speed up case-insensitive searches
# like lower(name) = lower('query');
cursor.execute("CREATE INDEX idx_name ON taxonomy (lower(name));")
cursor.execute("CREATE INDEX idx_tax_id_version_date ON taxonomy (tax_id, version_date);")
cursor.execute("CREATE INDEX idx_name_version_date ON taxonomy (name, version_date);")

# Full Text Search (FTS) index
print("--- creating full text index")
cursor.execute("CREATE VIRTUAL TABLE name_fts USING fts5(name);")
cursor.execute("INSERT INTO name_fts (name) SELECT name FROM taxonomy;")

conn.commit()

print("--- wrapping up")
# cursor.execute("PRAGMA synchronous = FULL;")
# cursor.execute("PRAGMA journal_mode = DELETE;")

conn.close()
