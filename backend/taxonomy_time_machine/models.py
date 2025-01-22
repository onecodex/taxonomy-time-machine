import sqlite3
from datetime import datetime
from typing import Literal

from dataclasses import dataclass
from enum import Enum


class EventName(Enum):
    Create = "create"
    Delete = "delete"
    Update = "alter"  # TODO: change me to Update


@dataclass
class Event:
    event_name: EventName
    tax_id: str
    version_date: datetime
    name: str | None = None
    rank: str | None = None
    parent_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict):
        version_date = data["version_date"]

        if type(version_date) is str:
            version_date = datetime.fromisoformat(data["version_date"])

        return cls(
            event_name=EventName(data["event_name"]),  # Convert to enum
            tax_id=data["tax_id"],
            version_date=version_date,
            name=data.get("name"),
            rank=data.get("rank"),
            parent_id=data.get("parent_id"),
        )

    def to_dict(self) -> dict:
        return {
            "event_name": self.event_name.value,
            "version_date": self.version_date,
            "tax_id": self.tax_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "rank": self.rank,
        }


def _get_all_events_recursive(
    db: "Taxonomy", tax_id: str, seen_tax_ids: set | None = None
) -> list[Event]:
    """
    Find all events for a given tax ID and any events for its parent's and
    their parents, etc...

    TODO: also find all events for the children of a tax ID

    TODO: this sometimes finds irrelevant events like a new node is created
    under a node in the lineage but isn't directly part of the current taxon's
    lineage
    """

    events: list[Event] = []

    if seen_tax_ids is None:
        seen_tax_ids = set()

    if tax_id in seen_tax_ids:
        return events

    seen_tax_ids.add(tax_id)

    for event in db.get_events(tax_id):
        events.append(event)
        seen_tax_ids.add(event.tax_id)
        if event.parent_id and event.parent_id not in seen_tax_ids:
            events.extend(
                _get_all_events_recursive(db, tax_id=event.parent_id, seen_tax_ids=seen_tax_ids)
            )

        seen_tax_ids.add(event.parent_id)

    return sorted(events, key=lambda e: e.version_date)


class Taxonomy:
    def __init__(self, database_path: str = "events.db"):
        self.conn = sqlite3.connect(database_path)
        self.conn.row_factory = sqlite3.Row  # return Row instead of tuple
        self.cursor = self.conn.cursor()

    def search_names(self, query: str, limit: int | None = 10) -> list[Event]:
        matches: list[dict] = []
        exact_matches: list[dict] = []

        # first, check if the query is tax-ID like
        if query.isnumeric():
            rows = self.cursor.execute(
                "SELECT * FROM taxonomy WHERE tax_id = ? ORDER BY version_date desc LIMIT 1",
                (query,),
            ).fetchall()

            exact_matches.extend([dict(r) for r in rows])

        if limit is None or (len(matches) + len(exact_matches) < limit):
            # first look for exact mathes (case insensitive)
            # LIKE is too slow...
            matches.extend(
                [
                    dict(r)
                    for r in self.cursor.execute(
                        """SELECT *
                        FROM taxonomy
                        WHERE name LIKE ?
                        ORDER BY LENGTH(name) ASC
                        LIMIT ?;
                        """,
                        (f"{query}%", 10),
                    ).fetchall()
                ]
            )

        if limit is None or (len(matches) + len(exact_matches)) < limit:
            # fuzzy matches
            matches.extend(
                [
                    dict(r)
                    for r in self.cursor.execute(
                        """
                    SELECT taxonomy.tax_id, taxonomy.name, taxonomy.rank, taxonomy.event_name, taxonomy.version_date
                    FROM name_fts
                    JOIN taxonomy ON name_fts.name = taxonomy.name
                    WHERE name_fts MATCH ?
                    ORDER BY LENGTH(taxonomy.name) ASC
                    LIMIT ?
                    ;
                    """,
                        (f'"{query}"', 10),
                    ).fetchall()
                ]
            )

        # sort by closest match (probably the shortest)
        matches = sorted(matches, key=lambda m: len(m["name"]))

        # exact matches should always come first
        # + truncate to limit
        # + convert to Events
        events = [Event.from_dict(m) for m in (exact_matches + matches)[:limit]]

        return events

    def get_events(
        self,
        tax_id: str,
        as_of: datetime | None = None,
        query_key: Literal["tax_id", "parent_id"] = "tax_id",
    ) -> list[Event]:
        """Get all events for a given tax_id or parent_id depending on
        query_key (default='tax_id')"""

        if query_key == "tax_id":
            self.cursor.execute("SELECT * FROM taxonomy WHERE tax_id = ?;", (tax_id,))
        elif query_key == "parent_id":
            self.cursor.execute("SELECT * FROM taxonomy WHERE parent_id = ?;", (tax_id,))
        else:
            raise Exception(f"Unable to use handle {query_key=}")

        rows = [Event.from_dict(dict(r)) for r in self.cursor.fetchall()]

        if as_of:
            rows = [r for r in rows if r.version_date <= as_of]

        return sorted(rows, key=lambda r: r.version_date)

    def get_children(self, tax_id: str, as_of: datetime | None = None):
        """Get all children of a node at a given version"""

        # 1. find all? rows where parent_id=query_tax_id using their tax_ids
        # ....

        # find all create/alter events where parent_id = tax_id and
        # version_date <= as_of
        parent_events = self.get_events(tax_id=tax_id, as_of=as_of, query_key="parent_id")

        # 2. find most recent event by tax ID and make sure that the parent is
        # *still* query_tax_id. remove these rows

        child_tax_ids = {e.tax_id for e in parent_events}
        deleted_tax_ids = {e.tax_id for e in parent_events if e.event_name is EventName.Delete}
        child_events = []

        # TODO: do this in a single db query
        for child_tax_id in child_tax_ids:
            if ee := self.get_events(tax_id=child_tax_id, as_of=as_of, query_key="tax_id"):
                last_event = ee[-1]

                # catch tax IDs that were deleted then re-created
                if (
                    last_event.event_name is not EventName.Delete
                    and last_event.tax_id in deleted_tax_ids
                ):
                    deleted_tax_ids.remove(last_event.tax_id)
                child_events.append(ee[-1])

        keep_tax_ids = {c.tax_id for c in child_events if c.parent_id == tax_id}
        events = [e for e in parent_events if e.tax_id in keep_tax_ids]

        # 3. remove any deleted rows
        events = [e for e in events if e.tax_id not in deleted_tax_ids]

        # for each tax ID, get the *latest* parent_id
        # if that parent_id == tax_id then keep it

        # NOTE: it's faster to do this in Python than in SQL at least with the
        # queries I tried.

        latest_row_by_tax_id: dict[str, Event] = {}
        for event in events:
            if event.tax_id not in latest_row_by_tax_id or (
                event.version_date >= latest_row_by_tax_id[event.tax_id].version_date
            ):
                latest_row_by_tax_id[event.tax_id] = event

        # if the taxon moved then we can't find it by parent ID because it has
        # a new parent ID... so we need to look up each individual taxon's
        # events to check for moves and deletions...

        # make sure the row is still a child of tax_id
        rows = [r for r in latest_row_by_tax_id.values() if r.parent_id == tax_id]

        # remove anything that got deleted
        rows = [r for r in rows if r.event_name is not EventName.Delete]

        return rows

    def get_all_events_recursive(self, tax_id: str) -> list[Event]:
        return _get_all_events_recursive(db=self, tax_id=tax_id)

    def get_versions(self, tax_id: str) -> list[datetime]:
        """Get the collapsed list of dates at which a taxon's lineage
        changed"""

        # TODO: handle deletions (example: 352463)

        events = _get_all_events_recursive(db=self, tax_id=tax_id)
        version_dates = sorted({e.version_date for e in events})

        seen_lineages = set()
        versions_with_changes = []

        for version_date in version_dates:
            events = self.get_lineage(tax_id=tax_id, as_of=version_date)

            # TODO: can a tax_id by deleted and created in the same version?
            # TODO: can a tax_id be re-created after being deleted?

            key = tuple([(e.rank, e.tax_id, e.parent_id, e.name) for e in events])

            # prevents versions where the tax ID didn't exist yet from showing
            # up for some reason
            if len(key) == 0:
                continue

            if key not in seen_lineages:
                versions_with_changes.append(version_date)
            seen_lineages.add(key)

        return versions_with_changes

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
                if event.parent_id:
                    parent = event
                    break

            if parent is not None:
                lineage.append(parent)
            else:
                break

            if parent.parent_id is None:
                break

            tax_id = parent.parent_id

        return lineage
