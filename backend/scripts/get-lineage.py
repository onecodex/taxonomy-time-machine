#!/usr/bin/env python3

import sqlite3

tax_id = 418784

conn = sqlite3.connect("events.db")

cursor = conn.cursor()


def get_events(tax_id: int) -> list:
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
            print(tax_id, parent_id, rank, name)
        else:
            break

        tax_id = parent_id


get_lineage(tax_id)
