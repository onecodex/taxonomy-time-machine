import sqlite3
from datetime import datetime
from typing import Literal

from functools import lru_cache


def coerce_row(row):
    row = dict(row)
    if "version_date" in row:
        # TODO: handle this in the scopenapi/hema?
        row["version_date"] = datetime.fromisoformat(row["version_date"])
    return row


def _get_all_events_recursive(db: "Taxonomy", tax_id: str, seen_tax_ids: set | None = None):
    """
    Find all events for a given tax ID and any events for its parent's and
    their parents, etc...

    TODO: also find all events for the children of a tax ID

    TODO: this sometimes finds irrelevant events like a new node is created
    under a node in the lineage but isn't directly part of the current taxon's
    lineage
    """

    events = db.get_events(tax_id=tax_id)

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

    @lru_cache
    def search_names(self, query: str, limit: int | None = 10) -> list[dict]:
        matches = []

        # first, check if the query is tax-ID like
        if query.isnumeric():
            rows = self.cursor.execute(
                "SELECT * FROM taxonomy WHERE tax_id = ? ORDER BY version_date desc LIMIT 1",
                (query,),
            ).fetchall()

            matches.extend([dict(r) for r in rows])

        # first look for exact mathes (case insensitive)
        # LIKE is too slow...
        matches.extend(
            self.cursor.execute(
                f"SELECT * FROM taxonomy WHERE name LIKE ?;", (f"{query}%",)
            ).fetchall()
        )

        if limit is None or len(matches) < limit:
            # fuzzy matches
            matches.extend(
                self.cursor.execute(
                    f"""
                    SELECT taxonomy.tax_id, taxonomy.name, taxonomy.rank, taxonomy.event_name, taxonomy.version_date
                    FROM name_fts
                    JOIN taxonomy ON name_fts.name = taxonomy.name
                    WHERE name_fts MATCH ? order by name_fts.rank
                    LIMIT ?
                    ;
                    """,
                    (f'"{query}"', limit or 10),
                ).fetchall()
            )

        tax_ids = set()
        results = []

        for row in matches:
            # TODO: handle this in the query
            if row["tax_id"] in tax_ids:
                continue

            results.append(coerce_row(row))
            tax_ids.add(row["tax_id"])

        return results[:limit]

    @lru_cache
    def get_events(
        self,
        tax_id: str,
        as_of: datetime | None = None,
        query_key: Literal["tax_id", "parent_id"] = "tax_id",
    ) -> list:
        """Get all events for a given tax_id or parent_id depending on
        query_key (default='tax_id')"""

        if query_key == "tax_id":
            self.cursor.execute(f"SELECT * FROM taxonomy WHERE tax_id = ?;", (tax_id,))
        elif query_key == "parent_id":
            self.cursor.execute(f"SELECT * FROM taxonomy WHERE parent_id = ?;", (tax_id,))
        else:
            raise Exception(f"Unable to use handle {query_key=}")

        rows = [dict(r) for r in self.cursor.fetchall()]

        # sqlite3 doesn't actually store dates as dates so we have to parse it
        # ourselves how quaint
        for row in rows:
            row["version_date"] = datetime.fromisoformat(row["version_date"])

        if as_of:
            rows = [r for r in rows if r["version_date"] <= as_of]

        rows = sorted(rows, key=lambda r: r["version_date"])

        return rows

    @lru_cache
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
        rows = rows
        return rows

    @lru_cache
    def get_all_events_recursive(self, tax_id: str) -> list[dict]:
        return _get_all_events_recursive(db=self, tax_id=tax_id)

    @lru_cache
    def get_versions(self, tax_id: str) -> list[datetime]:
        """Get the collapsed list of dates at which a taxon's lineage
        changed"""

        events = _get_all_events_recursive(db=self, tax_id=tax_id)
        version_dates = sorted({e["version_date"] for e in events})

        seen_lineages = set()
        versions_with_changes = []

        for version_date in version_dates:
            events = self.get_lineage(tax_id=tax_id, as_of=version_date)

            key = tuple([(e["rank"], e["tax_id"], e["parent_id"], e["name"]) for e in events])

            # prevents versions where the tax ID didn't exist yet from showing
            # up for some reason
            if len(key) == 0:
                continue

            if key not in seen_lineages:
                versions_with_changes.append(version_date)
            seen_lineages.add(key)

        return versions_with_changes

    @lru_cache
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