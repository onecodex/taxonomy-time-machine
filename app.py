import sqlite3
import polars as pl
from datetime import datetime
from typing import Literal
from flask import Flask, request, jsonify


def get_all_events_recursive(db: "Db", tax_id: str, seen_tax_ids: set | None = None):
    """
    Find all events for a given tax ID and any events for its parent's and
    their parents, etc...

    TODO: also find all events for the children of a tax ID
    """
    events: list[dict] = []

    if seen_tax_ids is None:
        seen_tax_ids = set()

    if tax_id in seen_tax_ids:
        return events

    seen_tax_ids.add(tax_id)

    for event in db.get_events(tax_id):
        events.append(event)

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
        self.conn.row_factory = sqlite3.Row  # return Row instead of tuple
        self.cursor = self.conn.cursor()

    def get_events(
        self,
        tax_id: str,
        as_of: datetime | None = None,
        query_key: Literal["tax_id", "parent_id"] = "tax_id",
    ) -> list:
        """Get all events for a given tax_id or parent_id depending on
        query_key (default='tax_id')"""
        self.cursor.execute(f"SELECT * FROM taxonomy WHERE {query_key} = {tax_id};")

        rows = [dict(r) for r in self.cursor.fetchall()]

        # sqlite3 doesn't actually store dates as dates so we have to parse it
        # ourselves how quaint
        for row in rows:
            row["version_date"] = datetime.fromisoformat(row["version_date"])

        if as_of:
            rows = [r for r in rows if r["version_date"] <= as_of]

        return rows

    def get_all_events_recursive(self, tax_id: str) -> list[dict]:
        return get_all_events_recursive(db=self, tax_id=tax_id)

    def get_lineage(self, tax_id: str, as_of: datetime | None = None):
        """
        Given a tax_id: return the taxonomy lineage. If `as_of` is specified,
        return the taxonomy lineage as of that date.
        """
        while True:
            events = self.get_events(tax_id=tax_id, as_of=as_of)

            # find most recent event where the parent_id changed
            parent = None
            for event in events[::-1]:
                if event["parent_id"]:
                    parent = event
                    break

            if parent is not None:
                yield parent
            else:
                break

            tax_id = parent["parent_id"]


app = Flask(__name__)


@app.route("/lineage", methods=["GET"])
def lineage():
    db = Db()
    version = request.args.get("version")
    tax_id = request.args.get("tax_id")

    if version:
        version = datetime.fromisoformat(version)

    lineage = list(db.get_lineage(tax_id=tax_id, as_of=version))

    return jsonify(lineage)


@app.route("/search", methods=["GET"])
def search():
    db = Db()
    tax_id = request.args.get("tax_id")
    if tax_id:
        rows = db.get_all_events_recursive(tax_id=tax_id)

        # make this a string again...
        for row in rows:
            row["version_date"] = row["version_date"].isoformat()
        return jsonify(rows)
    else:
        return jsonify({"ok": True})


def main():
    db = Db()

    pl.Config.set_tbl_rows(-1)  # Display all rows

    events = db.get_events("498019")

    print(pl.DataFrame(events))

    as_of_date = datetime.strptime("2020-01-01", "%Y-%m-%d")
    print(pl.DataFrame(db.get_lineage("498019", as_of=as_of_date)))

    print(pl.DataFrame(db.get_all_events_recursive("498019")))

    app.run(debug=True)


if __name__ == "__main__":
    main()
