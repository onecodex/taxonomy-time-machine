import sqlite3
import polars as pl
from datetime import datetime
from flask import Flask, request, jsonify


def get_all_events_recursive(db: "Db", tax_id: str, seen_tax_ids: set | None = None):
    events: list[dict] = []

    if seen_tax_ids is None:
        seen_tax_ids = set()

    if tax_id in seen_tax_ids:
        return events

    seen_tax_ids.add(tax_id)

    for event in db.get_events(tax_id):
        events.append(event)

        if event["tax_id"] not in seen_tax_ids:
            events.extend(
                get_all_events_recursive(db, tax_id=event["tax_id"], seen_tax_ids=seen_tax_ids)
            )

        seen_tax_ids.add(event["tax_id"])

        if event["parent_id"] and event["parent_id"] not in seen_tax_ids:
            events.extend(
                get_all_events_recursive(db, tax_id=event["parent_id"], seen_tax_ids=seen_tax_ids)
            )

        seen_tax_ids.add(event["parent_id"])

    return sorted(events, key=lambda e: e["version_date"])


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

    def get_all_events_recursive(self, tax_id: str) -> list[dict]:
        return get_all_events_recursive(db=self, tax_id=tax_id)

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


app = Flask(__name__)


@app.route("/search", methods=["GET"])
def search():
    db = Db()
    tax_id = request.args.get("tax_id")
    if tax_id:
        results = db.get_events(tax_id=tax_id)
        print(results)
        return jsonify(results)
    else:
        return jsonify({"ok": True})


# if __name__ == "__main__":
#    app.run(debug=True)


def main():
    db = Db()

    pl.Config.set_tbl_rows(-1)  # None displays all rows

    events = db.get_events("498019")

    up_to_date = datetime.strptime("2020-01-01", "%Y-%m-%d")

    # print(pl.DataFrame(events))

    # print(pl.DataFrame(db.get_lineage("498019", up_to=up_to_date)))

    print(pl.DataFrame(db.get_all_events_recursive("498019")))


if __name__ == "__main__":
    main()
