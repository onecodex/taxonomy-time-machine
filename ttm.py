#!/usr/bin/env python3

# create initial table

from collections import Counter
import csv
from pathlib import Path
import taxonomy
from datetime import datetime

# iterate over tax_id, parent_id, name, rank

taxdumps = sorted(
    [p for p in Path("dumps").glob("*") if p.is_dir()],
    key=lambda p: datetime.strptime(p.name.split("_")[1], "%Y-%m-%d"),
)

tax_info = set()

counts: Counter[bool] = Counter()

total_seen_rows = 0

# downsample for testing
# taxdumps = taxdumps[::10]

print(f"--- loading {len(taxdumps):,} taxdumps")

with open("taxonomy-data.csv", "wt") as handle:
    for n, taxdump in enumerate(taxdumps):
        writer = csv.writer(handle)

        print(f"--- {n} {taxdump}")
        tax = taxonomy.Taxonomy.from_ncbi(str(taxdump))
        counts_batch: Counter[bool] = Counter()

        for tax_id in tax:
            node = tax[tax_id]
            info = (node.id, node.parent, node.rank, node.name)
            is_new = info not in tax_info
            counts[is_new] += 1
            counts_batch[is_new] += 1

            tax_info.add(info)
            total_seen_rows += 1

            if is_new:
                writer.writerow([tax_id, node.parent, taxdump, node.name, node.rank])

        total = counts[True] + counts[False]
        total_batch = counts_batch[True] + counts_batch[False]

        print(taxdump)
        print(f"TOTAL new={counts[True]:,} ({counts[True]/total:.0%}) total={total:,}")
        print(
            f"BATCH new={counts_batch[True]:,} ({counts_batch[True]/total_batch:.0%}) total={total_batch:,}"
        )
        print(f"** total unique rows: {len(tax_info):,} {total_seen_rows=:,} **")
