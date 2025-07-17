#!/usr/bin/env python3

import argparse
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

from taxonomy import Taxonomy
from tqdm import tqdm

from . import Event, EventName, TaxonomyTimeMachine


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", required=True, type=str, help="path to output sqltie database")
    return parser.parse_args()


def dump_path_to_datetime(dump_path: Path) -> datetime:
    return datetime.strptime(dump_path.name.split("_")[1], "%Y-%m-%d")


def load_current_tax_id_to_node(database_path: str) -> dict[str, Event]:
    """Load current tax ID to node state"""

    return TaxonomyTimeMachine(database_path=database_path).iter_most_recent_events()


# TODO: use legit migrations framework
def prepare_db(cursor):
    # Optimized PRAGMA settings for faster inserts
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")
    cursor.execute("PRAGMA temp_store = MEMORY;")

    # Drop existing indices if they exist
    cursor.execute("DROP INDEX IF EXISTS idx_tax_id;")
    cursor.execute("DROP INDEX IF EXISTS idx_parent_id;")
    cursor.execute("DROP INDEX IF EXISTS idx_name;")
    cursor.execute("DROP INDEX IF EXISTS idx_tax_id_version_date;")
    cursor.execute("DROP INDEX IF EXISTS idx_name_version_date;")
    cursor.execute("DROP TABLE IF EXISTS name_fts;")

    # Create table
    # We use TEXT for tax_id and parent_id to support non-NCBI taxonomies such
    # as GTDB-Tk which lack IDs
    # (you can use the name as the ID)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS taxonomy_source (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT,
        version_date DATETIME
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS taxonomy (
        taxonomy_source_id INTEGER,
        event_name TEXT,
        version_date DATETIME,
        tax_id TEXT,
        parent_id TEXT,
        rank TEXT,
        name TEXT,
        FOREIGN KEY (taxonomy_source_id) REFERENCES taxonomy_source(id)
    )
    """)


def finalize_db(cursor):
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


def main() -> None:
    args = parse_args()

    # Connect to the SQLite database
    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()

    # stores the *last* state of a Tax ID
    # used to determine if a tax ID has changed

    # do this before dropping all indexes in `prepare_db` so we can leverage the index
    tax_id_to_node: dict[str, Event]
    try:
        tax_id_to_node = load_current_tax_id_to_node(args.db_path)
    except sqlite3.OperationalError:  # table doesn't exist yet... starting from scratch
        tax_id_to_node = {}

    # this drops the index because I think it's faster to re-add the index at the end
    # TODO: verify that..
    prepare_db(cursor)
    conn.commit()

    taxdump_paths = sorted(
        [p for p in Path("dumps").glob("*") if p.is_dir()],
        key=dump_path_to_datetime,
    )

    paths_to_import = []

    for taxdump_path in taxdump_paths:
        cursor.execute("SELECT count(*) FROM taxonomy_source WHERE path = ?", (str(taxdump_path),))
        count = cursor.fetchone()[0]
        if not count:
            paths_to_import.append(taxdump_path)

    n_events = 0

    print(f"Found {len(tax_id_to_node):,} existing taxonomy versions")

    data_to_insert: list[dict] = []
    last_tax_ids: None | set[str] = None

    total_seen_taxa = 0

    last_tax = None

    for n, taxdump_path in enumerate(paths_to_import):
        taxdump_date = dump_path_to_datetime(taxdump_path)

        cursor.execute(
            "INSERT INTO taxonomy_source (path, version_date) VALUES (?, ?) RETURNING id",
            (str(taxdump_path), taxdump_date),
        )
        taxonomy_source_id = cursor.fetchone()[0]
        conn.commit()

        tax = Taxonomy.from_ncbi(str(taxdump_path))
        print(f"--- loaded {taxdump_path}: {tax}")

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

            # node isn't in tax_id_to_node -- it must be new
            if from_node is None:
                event = Event(
                    event_name=EventName.Create,
                    tax_id=to_node.id,
                    rank=to_node.rank,
                    name=to_node.name,
                    parent_id=to_node.parent,
                    version_date=taxdump_date,
                    taxonomy_source_id=taxonomy_source_id,
                )
            # *something* changed
            elif (from_node.parent_id, from_node.rank, from_node.name) != (
                to_node.parent,
                to_node.rank,
                to_node.name,
            ):
                event = Event(
                    event_name=EventName.Update,
                    tax_id=to_node.id,
                    rank=to_node.rank,
                    name=to_node.name,
                    parent_id=to_node.parent,
                    version_date=taxdump_date,
                    taxonomy_source_id=taxonomy_source_id,
                )

            if event is not None:
                tax_id_to_node[tax_id] = event
                events.append(event)
                n_new_events += 1

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
                        taxonomy_source_id=taxonomy_source_id,
                    )
                )

                # remove from tax_id_to_node in case this tax ID gets re-created
                del tax_id_to_node[tax_id]
        last_tax_ids = seen_tax_ids

        for event in events:
            event_counts[event.event_name] += 1
            data_to_insert.append(event.to_dict())
            n_events += 1

        print(f"{n}/{len(taxdump_paths)} total_events={n_events:,} n_new_events={n_new_events:,}")

        for event_name, count in event_counts.items():
            print(f"    {event_name.value:>10} -> {count:,}")

        print()
        last_tax = tax

    print(Counter([event["event_name"] for event in data_to_insert]))

    print(f"--- {total_seen_taxa=:,}")
    print(f"--- {len(data_to_insert)=:,}")
    print(f"--- savings={1 - (len(data_to_insert) / total_seen_taxa):.2%}")

    batch_size = 10_000

    # Loop through data in batches to avoid memory overload
    # Batch insert using transactions and executemany
    for i in tqdm(range(0, len(data_to_insert), batch_size)):
        batch = data_to_insert[i : i + batch_size]
        cursor.executemany(
            """
            INSERT INTO taxonomy (event_name, version_date, tax_id, parent_id, rank, name, taxonomy_source_id)
            VALUES (:event_name, :version_date, :tax_id, :parent_id, :rank, :name, :taxonomy_source_id)
        """,
            batch,
        )

    conn.commit()

    print("--- wrapping up")

    cursor.execute("select count(*) from taxonomy")
    count = cursor.fetchone()[0]
    print(f"taxonomy version table now has {count:,} rows")

    finalize_db(cursor)
    conn.commit()

    conn.close()


if __name__ == "__main__":
    main()
