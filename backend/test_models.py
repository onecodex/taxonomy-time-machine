from datetime import datetime

import pytest

from taxonomy_time_machine import Event, EventName

D1 = datetime(2014, 8, 1)
D2 = datetime(2014, 9, 1)
D3 = datetime(2019, 5, 1)
D4 = datetime(2024, 12, 11)


def test_search_names(db):
    matches = [m.to_dict() for m in db.search_names("Drosophila", limit=None)]
    assert matches
    for match in matches:
        assert "tax_id" in match
        assert "rank" in match
        assert "name" in match
        assert "event_name" in match
        assert "version_date" in match
        assert type(match["version_date"]) is datetime
    names = {m["name"] for m in matches}
    assert "Drosophila" in names
    assert "Drosophila melanogaster" in names


def test_search_names_numeric(db):
    # First hit should always be the exact tax ID match
    matches = [m.to_dict() for m in db.search_names("4932", limit=None)]
    assert matches[0]["name"] == "Saccharomyces cerevisiae"


def test_match_should_be_most_specific(db):
    matches = [m.to_dict() for m in db.search_names("Saccharomyces cere", limit=None)]
    assert matches[0]["name"] == "Saccharomyces cerevisiae"


def test_match_should_be_deduplicated(db):
    # Drosophila simulans has two taxonomy rows (create + alter) but should collapse to one result
    matches = [m.to_dict() for m in db.search_names("Drosophila simulans", limit=None)]
    assert len([m for m in matches if m["name"] == "Drosophila simulans"]) == 1


def test_get_children_deleted_node(db):
    events = db.get_events("1001")
    assert len(events) == 2
    assert events[0].parent_id == "1000"
    assert events[1].event_name is EventName.Delete

    events = db.get_events("1000", query_key="parent_id")
    assert len(events) == 2

    # No children after deletion
    assert db.get_children("1000") == []

    # Child exists before deletion
    assert db.get_children("1000", as_of=D1) == [
        Event.from_dict(
            {
                "event_name": "create",
                "name": "DeletedSpecies",
                "parent_id": "1000",
                "rank": "species",
                "tax_id": "1001",
                "version_date": D1,
                "taxonomy_source_id": 1,
            }
        )
    ]


@pytest.mark.parametrize(
    ["tax_id", "timestamp", "expected_names"],
    [
        ("1000", D1, {"DeletedSpecies"}),  # before deletion
        ("1000", None, set()),  # after deletion: no children
        ("2000", D1, {"MovedSpecies"}),  # before move
        ("2000", None, set()),  # after move: no children
        ("2001", None, {"MovedSpecies"}),  # new parent has the child
    ],
)
def test_children_scenarios(db, tax_id, timestamp, expected_names):
    children = db.get_children(tax_id, as_of=timestamp)
    assert {c.name for c in children} == expected_names


def test_get_children_moved_node(db):
    events = db.get_events("2002")
    assert len(events) == 2
    assert events[0].event_name is EventName.Create
    assert events[1].event_name is EventName.Update
    assert events[1].parent_id == "2001"

    # Before move: 2002 is under 2000
    assert len(db.get_children("2000", as_of=D1)) == 1
    # After move: 2000 has no children
    assert db.get_children("2000") == []


def test_search_names_special_characters(db):
    # Brackets in names should not cause FTS syntax errors and should return results
    matches = db.search_names("[Candida]", limit=10)
    assert any(m.name == "[Candida] auris" for m in matches)


def test_get_events(db):
    events = db.get_events("821")
    assert events
    assert len(events) == 2


def test_get_all_events_recursive(db):
    events = db.get_all_events_recursive("821")
    assert events
    tax_ids = {e.tax_id for e in events}
    assert "821" in tax_ids
    assert "100" in tax_ids
    assert "10" in tax_ids


def test_get_versions(db):
    versions = db.get_versions("821")
    assert versions

    lineages = []
    for version in versions:
        events = db.get_lineage(tax_id="821", as_of=version)
        lineage_data = tuple([(e.rank, e.tax_id, e.parent_id, e.name) for e in events])
        lineages.append(lineage_data)

    # No lineages should be repeated
    assert len(lineages) == len(set(lineages))


def test_get_versions_deleted_node_stops_at_deletion(db):
    # 1001 was deleted at D2; its parent was renamed at D3
    # versions should not include D3 or later
    versions = db.get_versions("1001")
    assert all(v <= D2 for v in versions), f"Expected no versions after D2, got {versions}"


def test_get_versions_deleted_node_includes_deletion_date(db):
    # D2 is the deletion date and must always appear as a dot on the timeline
    versions = db.get_versions("1001")
    assert D2 in versions, f"Expected deletion date D2 in versions, got {versions}"


def test_get_versions_deleted_node_includes_creation(db):
    # D1 is when 1001 was created — should still appear
    versions = db.get_versions("1001")
    assert D1 in versions, f"Expected creation date D1 in versions, got {versions}"


def test_get_children(db):
    children = db.get_children(tax_id="3000")
    assert children
    # Each tax ID should appear only once
    assert len({c.tax_id for c in children}) == len(children)

    children_at_d1 = db.get_children(tax_id="3000", as_of=D1)
    assert children_at_d1
    assert len({c.tax_id for c in children_at_d1}) == len(children_at_d1)


def test_lineage(db):
    events = db.get_lineage(tax_id="821", as_of=D4)
    assert [x.name for x in events] == [
        "Phocaeicola vulgatus",
        "Bacteroides",
        "Bacteroidota",
        "Bacteria",
    ]

    events = db.get_lineage(tax_id="821", as_of=D1)
    assert [x.name for x in events] == [
        "Bacteroides vulgatus",
        "Bacteroides",
        "Bacteroidetes",
        "Bacteria",
    ]
