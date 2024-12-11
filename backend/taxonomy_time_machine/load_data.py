#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
from tqdm import tqdm
import taxonomy
from datetime import datetime
import argparse

import sqlite3

from models import Event, EventName


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--always-insert",
        action="store_true",
        default=False,
        help="Always insert nodes instead of only inserting deltas",
    )
    parser.add_argument("--db-path", required=True, type=str, help="path to output sqltie database")
    parser.add_argument("--n-dumps", default=None, type=int, help="Only add first n taxonomy dumps")
    return parser.parse_args()


def dump_path_to_datetime(dump_path: Path) -> datetime:
    return datetime.strptime(dump_path.name.split("_")[1], "%Y-%m-%d")


def main() -> None:
    args = parse_args()

    taxdumps = sorted(
        [p for p in Path("dumps").glob("*") if p.is_dir()],
        key=dump_path_to_datetime,
    )

    n_events = 0
    tax_id_to_node: dict = {}
    data_to_insert: list[dict] = []
    last_tax_ids: None | set[str] = None

    total_seen_taxa = 0

    last_tax = None

    if args.n_dumps:
        print(f"--- using first {args.n_dumps} taxdump archives")
        taxdumps = taxdumps[: args.n_dumps]

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

        for tax_id in tax:
            from_node = tax_id_to_node.get(tax_id)
            to_node = tax[tax_id]
            seen_tax_ids.add(tax_id)

            event = None

            if from_node is None:
                event = Event(
                    event_name=EventName.Create,
                    tax_id=to_node.id,
                    rank=to_node.rank,
                    name=to_node.name,
                    parent_id=to_node.parent,
                    version_date=taxdump_date,
                )
            elif args.always_insert or (
                (from_node.parent, from_node.rank, from_node.name)
                != (
                    to_node.parent,
                    to_node.rank,
                    to_node.name,
                )
            ):
                event = Event(
                    event_name=EventName.Update,
                    tax_id=to_node.id,
                    rank=to_node.rank,
                    name=to_node.name,
                    parent_id=to_node.parent,
                    version_date=taxdump_date,
                )

            if event is not None:
                events.append(event)
                n_new_events += 1

            tax_id_to_node[tax_id] = to_node

        # find all the deleted nodes

        # append deletions
        if last_tax_ids is not None:
            for tax_id in last_tax_ids - seen_tax_ids:
                # Store the parent_id so that we can find the deletion events by parent_id
                # (useful for excluding deleted children from get_children)
                events.append(
                    Event(
                        event_name=EventName.Delete,
                        tax_id=tax_id,
                        # taxonomy library type annotation is wrong?
                        parent_id=last_tax[tax_id].parent if last_tax else None,  # mypy: ignore
                        version_date=taxdump_date,
                    )
                )

                # remove from tax_id_to_node in case this tax ID gets re-created
                tax_id_to_node[tax_id] = None
        last_tax_ids = seen_tax_ids

        for event in events:
            event_counts[event.event_name] += 1
            data_to_insert.append(event.to_dict())
            n_events += 1

        print(f"{n}/{len(taxdumps)} total_events={n_events:,} n_new_events={n_new_events:,}")

        for event_name, count in event_counts.items():
            print(f"    {event_name.value:>10} -> {count:,}")

        print()
        # TODO: can probably clean up a lot of this code by just using `last_tax`
        last_tax = tax

    print(f"--- {total_seen_taxa=:,}")
    print(f"--- {len(data_to_insert)=:,}")
    print(f"--- savings={1 - (len(data_to_insert) / total_seen_taxa):.2%}")

    # TODO: write to sqlite while parsing to avoid having to store all taxonomy
    # nodes in memory...

    # Connect to the SQLite database
    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()

    # Optimized PRAGMA settings for faster inserts
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")
    cursor.execute("PRAGMA temp_store = MEMORY;")

    # Create table
    # We use TEXT for tax_id and parent_id to support non-NCBI taxonomies such
    # as GTDB-Tk which lack IDs
    # (you can use the name as the ID)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS taxonomy (
        event_name TEXT,
        version_date DATETIME,
        tax_id TEXT,
        parent_id TEXT,
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


if __name__ == "__main__":
    main()
