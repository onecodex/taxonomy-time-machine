#!/usr/bin/env python3

import taxonomy
from pathlib import Path
from datetime import datetime
import sqlite3

conn = sqlite3.connect("events.db")

cursor = conn.cursor()


def get_events(tax_id: str) -> list:
    cursor.execute(f"SELECT * FROM taxonomy WHERE tax_id = {tax_id};")
    events = list(cursor.fetchall())
    return events


def get_parent(events):
    for event_name, version, tax_id, parent_id, rank, name in events[::-1]:
        if parent_id:
            return (tax_id, parent_id, rank, name)

    return None


def get_lineage(tax_id):
    while True:
        events = get_events(tax_id=tax_id)
        parent = get_parent(events)
        if parent is not None:
            tax_id, parent_id, rank, name = parent
            yield (tax_id, parent_id, rank, name)
        else:
            break

        tax_id = parent_id


taxdumps = sorted(
    [p for p in Path("dumps").glob("*") if p.is_dir()],
    key=lambda p: datetime.strptime(p.name.split("_")[1], "%Y-%m-%d"),
)

dump = taxdumps[-1]

print(f"--- loading latest dump: {dump}")

tax = taxonomy.Taxonomy.from_ncbi(str(dump))

for n, tax_id in enumerate(tax, start=1):
    if n % 10000 == 0:
        print(f"checked {n:,} nodes")
    db_lineage = list(get_lineage(tax_id))
    tax_lineage = tax.lineage(tax_id)

    db_names = [x[3] for x in db_lineage]
    tax_names = [n.name for n in tax_lineage][:-1]  # trim root

    if "cellular organisms" in tax_names:
        if not db_names == tax_names:
            print(tax_id)
            print(db_names)
            print(tax_names)
            quit()
