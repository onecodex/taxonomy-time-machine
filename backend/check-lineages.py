#!/usr/bin/env python3

import taxonomy
from models import Taxonomy
from pathlib import Path
from datetime import datetime


event_taxonomy = Taxonomy(database_path="events.db")

taxdumps = sorted(
    [p for p in Path("dumps").glob("*") if p.is_dir()],
    key=lambda p: datetime.strptime(p.name.split("_")[1], "%Y-%m-%d"),
)


for n, dump in enumerate(taxdumps, start=1):
    print(f"--- testing {n} of {len(taxdumps)}: {dump}")

    tax = taxonomy.Taxonomy.from_ncbi(str(dump))

    for n, tax_id in enumerate(tax, start=1):
        if n % 10000 == 0:
            print(f"checked {n:,} nodes")

        db_lineage = list(event_taxonomy.get_lineage(tax_id))
        print([x["name"] for x in db_lineage])
        tax_lineage = tax.lineage(tax_id)

        db_names = [x["name"] for x in db_lineage]
        tax_names = [n.name for n in tax_lineage][:-1]  # trim root

        if db_names != tax_names:
            print(tax_id)
            print(db_names)
            print(tax_names)
            quit(1)
