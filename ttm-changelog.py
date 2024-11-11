#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import taxonomy
from datetime import datetime
import csv

from dataclasses import dataclass
from enum import Enum

# iterate over tax_id, parent_id, name, rank

taxdumps = sorted(
    [p for p in Path("dumps").glob("*") if p.is_dir()],
    key=lambda p: datetime.strptime(p.name.split("_")[1], "%Y-%m-%d"),
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

out_handle = open("events.csv", "w")
writer = csv.writer(out_handle)

for n, taxdump in enumerate(taxdumps):
    tax = taxonomy.Taxonomy.from_ncbi(str(taxdump))

    # TODO: also load merged.dmp and delnodes.dmp
    # can we infer deleted and merged from just names and nodes?

    n_new_events = 0

    starting_tax_ids: set[str] = set(tax_id_to_node.keys())
    seen_tax_ids: set[str] = set()

    event_counts: Counter[EventName] = Counter()

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
    for tax_id in starting_tax_ids - seen_tax_ids:
        events.append(Event(event_name=EventName.Delete, id=tax_id))

    for event in events:
        event_counts[event.event_name] += 1
        writer.writerow(
            [
                event.event_name.value,
                str(taxdump),
                event.id,
                event.parent_id,
                event.rank,
                event.name,
            ]
        )
        n_events += 1

    print(f"{n}/{len(taxdumps)} total_events={n_events:,} n_new_events={n_new_events:,}")

    for event_name, count in event_counts.items():
        print(f"    {event_name.value:>20} -> {count:,}")

    print()


out_handle.close()
