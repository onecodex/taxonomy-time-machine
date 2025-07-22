#!/usr/bin/env python3

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from taxonomy import Taxonomy
from tqdm import tqdm

from . import Event, EventName, TaxonomyTimeMachine
from .models import Base, TaxonomySource, Taxonomy as TaxonomyModel


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", required=True, type=str, help="path to output sqltie database")
    return parser.parse_args()


def dump_path_to_datetime(dump_path: Path) -> datetime:
    return datetime.strptime(dump_path.name.split("_")[1], "%Y-%m-%d")


def load_current_tax_id_to_node(database_path: str) -> dict[str, Event]:
    """Load current tax ID to node state"""

    return TaxonomyTimeMachine(database_path=database_path).iter_most_recent_events()


def setup_sqlite_performance(engine):
    """Optimize SQLite for bulk inserts"""
    with engine.connect() as conn:
        conn.execute(text("PRAGMA synchronous = OFF"))
        conn.execute(text("PRAGMA journal_mode = MEMORY"))
        conn.execute(text("PRAGMA temp_store = MEMORY"))
        conn.commit()


def main() -> None:
    args = parse_args()

    # Create SQLAlchemy engine and session
    engine = create_engine(f"sqlite:///{args.db_path}")
    Session = sessionmaker(bind=engine)

    # stores the *last* state of a Tax ID
    # used to determine if a tax ID has changed
    tax_id_to_node: dict[str, Event]
    try:
        tax_id_to_node = load_current_tax_id_to_node(args.db_path)
    except Exception:  # table doesn't exist yet... starting from scratch
        tax_id_to_node = {}

    # Optimize SQLite for bulk inserts
    setup_sqlite_performance(engine)

    taxdump_paths = sorted(
        [p for p in Path("dumps").glob("*") if p.is_dir()],
        key=dump_path_to_datetime,
    )

    paths_to_import = []

    with Session() as session:
        for taxdump_path in taxdump_paths:
            count = (
                session.query(TaxonomySource)
                .filter(TaxonomySource.path == str(taxdump_path))
                .count()
            )
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

        with Session() as session:
            taxonomy_source = TaxonomySource(path=str(taxdump_path), version_date=taxdump_date)
            session.add(taxonomy_source)
            session.commit()
            taxonomy_source_id = taxonomy_source.id

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

    # Batch insert using SQLAlchemy bulk operations
    with Session() as session:
        for i in tqdm(range(0, len(data_to_insert), batch_size)):
            batch = data_to_insert[i : i + batch_size]
            taxonomy_objects = [
                TaxonomyModel(
                    event_name=item["event_name"],
                    version_date=item["version_date"],
                    tax_id=item["tax_id"],
                    parent_id=item["parent_id"],
                    rank=item["rank"],
                    name=item["name"],
                    taxonomy_source_id=item["taxonomy_source_id"],
                )
                for item in batch
            ]
            session.bulk_save_objects(taxonomy_objects)
            session.commit()

    print("--- wrapping up")

    with Session() as session:
        count = session.query(TaxonomyModel).count()
        print(f"taxonomy version table now has {count:,} rows")


if __name__ == "__main__":
    main()
