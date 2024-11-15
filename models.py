import sqlite3
from datetime import datetime
from typing import Literal


def _get_all_events_recursive(db: "Taxonomy", tax_id: str, seen_tax_ids: set | None = None):
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
                _get_all_events_recursive(db, tax_id=event["parent_id"], seen_tax_ids=seen_tax_ids)
            )

        seen_tax_ids.add(event["parent_id"])

    return sorted(events, key=lambda e: e["version_date"])


class Taxonomy:
    def __init__(self, database_path: str = "events.db"):
        self.conn = sqlite3.connect(database_path)
        self.conn.row_factory = sqlite3.Row  # return Row instead of tuple
        self.cursor = self.conn.cursor()

    def search_names(self, query: str, limit: int = 10) -> list[dict]:
        matches = []

        # first look for exact mathes (case insensitive)
        # LIKE is too slow...
        matches.extend(
            self.cursor.execute(
                f"SELECT * from taxonomy WHERE lower(name) = lower('{query}');"
            ).fetchall()
        )

        print(matches)

        if len(matches) >= limit:
            return [dict(r) for r in matches]

        # fuzzy matches
        matches.extend(
            self.cursor.execute(
                f"SELECT * FROM name_fts WHERE name MATCH '{query}' order by rank;"
            ).fetchall()
        )
        return [dict(r) for r in matches][:limit]

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

        rows = [r for r in latest_row_by_tax_id.values() if r["parent_id"] == tax_id]

        # TODO: make this toggle-able
        rows = [r for r in rows if "sp. " not in r["name"]]

        # TODO: pagination
        rows = rows[:20]
        return rows

    def get_all_events_recursive(self, tax_id: str) -> list[dict]:
        return _get_all_events_recursive(db=self, tax_id=tax_id)

    def get_versions(self, tax_id: str) -> list[datetime]:
        """Get the collapsed list of dates at which a taxon's lineage
        changed"""
        events = _get_all_events_recursive(db=self, tax_id=tax_id)
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
