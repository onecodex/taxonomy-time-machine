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

    TODO: this sometimes finds irrelevant events like a new node is created
    under a node in the lineage but isn't directly part of the current taxon's
    lineage
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

    def search_names(self, query: str) -> list[dict]:
        matches = self.cursor.execute(f"SELECT * FROM name_fts WHERE name MATCH '{query}';")
        return [dict(r) for r in matches]

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

        rows = sorted(rows, key=lambda r: r["version_date"])

        return rows

    def get_children(self, tax_id: str, as_of=None):
        """Get all children of a node at a given version"""

        # find all create/alter events where parent_id = tax_id and
        # version_date <= as_of
        events = self.get_events(tax_id=tax_id, as_of=as_of, query_key="parent_id")

        # for each tax ID, get the *latest* parent_id
        # if that parent_id == tax_id then keep it

        # NOTE: it's faster to do this in Python than in SQL at least with the
        # queries I tried.

        latest_row_by_tax_id: dict[str, dict] = {}
        for event in events:
            if event["tax_id"] not in latest_row_by_tax_id or (
                event["version_date"] >= latest_row_by_tax_id[event["tax_id"]]["version_date"]
            ):
                latest_row_by_tax_id[event["tax_id"]] = event

        print(latest_row_by_tax_id)
        print(f"{tax_id=}")
        rows = [r for r in latest_row_by_tax_id.values() if r["parent_id"] == tax_id]
        print(rows)
        return rows

    def get_all_events_recursive(self, tax_id: str) -> list[dict]:
        return get_all_events_recursive(db=self, tax_id=tax_id)

    def get_versions(self, tax_id: str) -> list[datetime]:
        """Get the collapsed list of dates at which a taxon's lineage
        changed"""
        events = get_all_events_recursive(db=self, tax_id=tax_id)
        return sorted({e["version_date"] for e in events})

    def get_lineage(self, tax_id: str, as_of: datetime | None = None):
        """
        Given a tax_id: return the taxonomy lineage. If `as_of` is specified,
        return the taxonomy lineage as of that date.
        """

        lineage = []

        while True:
            events = self.get_events(tax_id=tax_id, as_of=as_of)

            # find most recent event where the parent_id changed
            parent = None
            for event in events[::-1]:
                if event["parent_id"]:
                    parent = event
                    break

            if parent is not None:
                lineage.append(parent)
            else:
                break

            tax_id = parent["parent_id"]

        return lineage


app = Flask(__name__)

# TODO: we can cut down on the number of DB queries by fetching the events
# first and then filtering them ...


@app.route("/events", methods=["GET"])
def events():
    db = Db()
    tax_id = request.args.get("tax_id")
    events = list(db.get_events(tax_id=tax_id))
    return jsonify(events)


@app.route("/children", methods=["GET"])
def children():
    db = Db()
    version = request.args.get("version")
    tax_id = int(request.args.get("tax_id"))

    if version:
        version = datetime.fromisoformat(version)

    children = list(db.get_children(tax_id=tax_id, as_of=version))

    print(children)

    return jsonify(children)


@app.route("/lineage", methods=["GET"])
def lineage():
    db = Db()
    version = request.args.get("version")
    tax_id = int(request.args.get("tax_id"))

    if version:
        version = datetime.fromisoformat(version)

    lineage = list(db.get_lineage(tax_id=tax_id, as_of=version))

    return jsonify(lineage)


@app.route("/versions", methods=["GET"])
def search():
    db = Db()
    tax_id = request.args.get("tax_id")
    if tax_id:
        versions = [{"version_date": v.isoformat()} for v in db.get_versions(tax_id=tax_id)]
        return jsonify(versions)
    else:
        return jsonify([])


def main():
    db = Db()

    pl.Config.set_tbl_rows(-1)  # Display all rows

    events = db.get_events("498019")

    pl.DataFrame(events)

    as_of_date = datetime.strptime("2020-01-01", "%Y-%m-%d")
    pl.DataFrame(db.get_lineage("498019", as_of=as_of_date))

    print(pl.DataFrame(db.get_all_events_recursive("498019")))

    app.run(debug=True)


if __name__ == "__main__":
    main()
