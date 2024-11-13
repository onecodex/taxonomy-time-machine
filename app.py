import sqlite3
import polars as pl
from datetime import datetime


class Db:
    def __init__(self):
        self.conn = sqlite3.connect("events.db")
        self.conn.row_factory = sqlite3.Row  # return dicts instead of tuples
        self.cursor = self.conn.cursor()

    def get_events(self, tax_id: str, up_to: str | None = None) -> list:
        """Get all events for a given tax_id"""
        self.cursor.execute(f"SELECT * FROM taxonomy WHERE tax_id = {tax_id};")

        rows = [dict(r) for r in self.cursor.fetchall()]

        # sqlite3 doesn't actually store dates as dates
        # so we have to parse it ourselves how quaint

        for row in rows:
            row["version_date"] = datetime.fromisoformat(row["version_date"])

        if up_to:
            rows = [r for r in rows if r["version_date"] <= up_to]

        return rows

    def _get_latest_parent(self, events) -> dict | None:
        for event in events[::-1]:
            if event["parent_id"]:
                return event

        return None

    def get_lineage(self, tax_id: str, up_to: str | None = None):
        """
        Given a tax_id: return the *current* taxonomic lineage
        """
        while True:
            events = self.get_events(tax_id=tax_id, up_to=up_to)
            parent = self._get_latest_parent(events)
            if parent is not None:
                yield parent
            else:
                break

            tax_id = parent["parent_id"]


def main():
    db = Db()

    events = db.get_events("498019")

    up_to_date = datetime.strptime("2024-01-01", "%Y-%m-%d")

    # print(pl.DataFrame(events))

    print(pl.DataFrame(db.get_lineage("498019", up_to=up_to_date)))


if __name__ == "__main__":
    main()
