import sqlite3
from datetime import datetime
from typing import Literal
from functools import lru_cache

from dataclasses import dataclass
from enum import Enum

import time
import logging

# Set logging level to INFO so profiling messages are visible
logging.basicConfig(level=logging.WARNING)


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

    def _profile(self, func_name: str, start: float, end: float):
        elapsed = (end - start) * 1000  # ms
        logging.info(f"[PROFILE] {func_name} took {elapsed:.2f} ms")

    def _escape_fts_phrase(self, text: str) -> str:
        """Escape text for use in FTS5 phrase queries by doubling quotes and wrapping in quotes"""
        # Escape internal quotes by doubling them (FTS5 standard)
        escaped = text.replace('"', '""')
        # Wrap in quotes to make it a phrase query
        return f'"{escaped}"'

    def _safe_fts_query(self, sql: str, params: tuple):
        """Execute FTS query with fallback to empty results on syntax errors"""
        try:
            return self.cursor.execute(sql, params).fetchall()
        except sqlite3.OperationalError as e:
            if "fts5: syntax error" in str(e).lower():
                logging.warning(
                    f"FTS syntax error with query: {params}, falling back to empty results"
                )
                return []
            else:
                # Re-raise other operational errors
                raise

    @lru_cache(maxsize=128)
    def search_names(self, query: str, limit: int | None = 10) -> list[Event]:
        _profile_start = time.perf_counter()
        matches: list[dict] = []
        exact_matches: list[dict] = []

        # first, check if the query is tax-ID like
        if query.isnumeric():
            _q1_start = time.perf_counter()
            rows = self.cursor.execute(
                """SELECT *
                FROM taxonomy
                WHERE tax_id = ?
                ORDER BY version_date desc
                LIMIT 1""",
                (query,),
            ).fetchall()
            _q1_end = time.perf_counter()
            self._profile("search_names:taxid_query", _q1_start, _q1_end)

            exact_matches.extend([dict(r) for r in rows])

        if limit is None or (len(matches) + len(exact_matches) < limit):
            # Use FTS for prefix matches instead of slow LIKE query
            _q2_start = time.perf_counter()
            prefix_rows = [
                dict(r)
                for r in self._safe_fts_query(
                    """
                    SELECT *
                    FROM name_fts
                    JOIN taxonomy ON name_fts.name = taxonomy.name
                    WHERE name_fts MATCH ?
                    ORDER BY LENGTH(taxonomy.name) ASC
                    LIMIT ?
                    ;
                    """,
                    (f"{self._escape_fts_phrase(query)}*", 10),
                )
            ]
            _q2_end = time.perf_counter()
            self._profile("search_names:prefix_query", _q2_start, _q2_end)
            matches.extend(prefix_rows)

        if limit is None or (len(matches) + len(exact_matches)) < limit:
            # fuzzy matches
            _q3_start = time.perf_counter()
            fuzzy_rows = [
                dict(r)
                for r in self._safe_fts_query(
                    """
                    SELECT taxonomy.tax_id, taxonomy.name, taxonomy.rank, taxonomy.event_name, taxonomy.version_date
                    FROM name_fts
                    JOIN taxonomy ON name_fts.name = taxonomy.name
                    WHERE name_fts MATCH ?
                    ORDER BY LENGTH(taxonomy.name) ASC
                    LIMIT ?
                    ;
                    """,
                    (self._escape_fts_phrase(query), 10),
                )
            ]
            _q3_end = time.perf_counter()
            self._profile("search_names:fuzzy_query", _q3_start, _q3_end)
            matches.extend(fuzzy_rows)

        # sort by closest match (probably the shortest)
        matches = sorted(matches, key=lambda m: len(m["name"]))

        # exact matches should always come first
        # + convert to Events
        events = [Event.from_dict(m) for m in (exact_matches + matches)]

        # deduplicate by name, taking most-recent
        name_to_event: dict[str, Event] = {}
        for event in events:
            existing_event = name_to_event.get(event.name)
            if existing_event is None:
                name_to_event[event.name] = event
            elif existing_event.version_date < event.version_date:
                name_to_event[event.name] = event

        events = list(name_to_event.values())

        # + truncate to limit
        events = events[:limit]

        self._profile("search_names", _profile_start, time.perf_counter())
        return events

    @lru_cache(maxsize=256)
    def get_events(
        self,
        tax_id: str,
        as_of: datetime | None = None,
        query_key: Literal["tax_id", "parent_id"] = "tax_id",
    ) -> list[Event]:
        """Get all events for a given tax_id or parent_id depending on
        query_key (default='tax_id')"""
        _profile_start = time.perf_counter()

        if query_key == "tax_id":
            self.cursor.execute("SELECT * FROM taxonomy WHERE tax_id = ?;", (tax_id,))
        elif query_key == "parent_id":
            self.cursor.execute("SELECT * FROM taxonomy WHERE parent_id = ?;", (tax_id,))
        else:
            raise Exception(f"Unable to use handle {query_key=}")

        rows = [Event.from_dict(dict(r)) for r in self.cursor.fetchall()]

        if as_of:
            rows = [r for r in rows if r.version_date <= as_of]

        result = sorted(rows, key=lambda r: r.version_date)
        self._profile("get_events", _profile_start, time.perf_counter())
        return result

    @lru_cache(maxsize=256)
    def get_children(self, tax_id: str, as_of: datetime | None = None):
        """Get all children of a node at a given version"""

        _profile_start = time.perf_counter()

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

        self._profile("get_children", _profile_start, time.perf_counter())
        return rows

    def get_all_events_recursive(self, tax_id: str) -> list[Event]:
        _profile_start = time.perf_counter()
        result = _get_all_events_recursive(db=self, tax_id=tax_id)
        self._profile("get_all_events_recursive", _profile_start, time.perf_counter())
        return result

    @lru_cache(maxsize=256)
    def get_versions(self, tax_id: str) -> list[datetime]:
        """Get the collapsed list of dates at which a taxon's lineage
        changed"""
        _profile_start = time.perf_counter()

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

        self._profile("get_versions", _profile_start, time.perf_counter())
        return versions_with_changes

    @lru_cache(maxsize=256)
    def get_lineage(self, tax_id: str, as_of: datetime | None = None):
        """
        Given a tax_id: return the taxonomy lineage. If `as_of` is specified,
        return the taxonomy lineage as of that date.
        """
        _profile_start = time.perf_counter()

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

        self._profile("get_lineage", _profile_start, time.perf_counter())
        return lineage
