#!/usr/bin/env python3

import taxonomy
from tqdm import tqdm
from pathlib import Path
from datetime import datetime

from models import Taxonomy as TaxonomyTimeMachine

ttm = TaxonomyTimeMachine("events.db")

taxdumps = sorted(
    [p for p in Path("dumps").glob("*") if p.is_dir()],
    key=lambda p: datetime.strptime(p.name.split("_")[1], "%Y-%m-%d"),
)


def dump_path_to_datetime(dump_path: Path):
    return datetime.strptime(dump_path.name.split("_")[1], "%Y-%m-%d")


total_checked = 0
total_passed = 0
total_failed = 0


with open("failed.txt", "wt") as out_handle:
    # skip first dump, nothing interesting happens yet
    for n, taxdump in enumerate(taxdumps, start=1):
        print(f"--- loading {n} of {len(taxdumps)} dump: {taxdump}")

        tax = taxonomy.Taxonomy.from_ncbi(str(taxdump))

        timestamp = dump_path_to_datetime(taxdump)

        n_checked, n_passed, n_failed = 0, 0, 0

        for tax_id in tqdm(tax):
            db_lineage = list(ttm.get_lineage(tax_id, as_of=timestamp))
            tax_lineage = tax.lineage(tax_id)

            tax_children = tax.children(tax_id)
            db_children = list(ttm.get_children(tax_id, as_of=timestamp))

            db_lineage_names = [x.name for x in db_lineage]
            tax_lineage_names = [n.name for n in tax_lineage][:-1]  # trim root

            db_children_names = {n.name for n in db_children}
            tax_children_names = {n.name for n in tax_children}

            if (db_lineage_names != tax_lineage_names) or (db_children_names != tax_children_names):
                n_failed += 1
            else:
                n_passed += 1

            if n_failed:
                print(timestamp)
                print(tax_id)
                print(db_children_names ^ tax_children_names)
                out_handle.write(f"{timestamp}\t{tax_id}\n")

        total_checked += n_failed + n_passed
        total_failed += n_failed
        total_passed += n_passed

        print(f"{n_passed=:,} {n_failed=:,}")

print(f"{total_passed=:,}")
print(f"{total_failed=:,}")
print(f"{total_checked=:,}")
