import pytest

import taxonomy
from models import Taxonomy
from datetime import datetime


@pytest.fixture
def db():
    return Taxonomy()


def test_search_names(db):
    matches = db.search_names("Drosophila", limit=None)

    # matches should all have full taxonomic data
    for match in matches:
        assert "tax_id" in match
        assert "rank" in match
        assert "name" in match
        assert "event_name" in match
        assert "version_date" in match
        assert type(match["version_date"]) is datetime

    # data should be uniquified
    assert len({m["tax_id"] for m in matches}) == len(matches)

    assert matches


def test_get_children_deleted_node(db):
    # currently, this node has no children because it was deleted
    events = db.get_events("352463")

    assert len(events) == 2

    assert events[0]["parent_id"] == 188979
    assert events[1]["event_name"] == "delete"

    # the deletion event should show up here...
    # TODO: move this to a test of `get_events`
    events = db.get_events("188979", query_key="parent_id")
    assert len(events) == 2

    # no children, because the child was deleted
    assert db.get_children("188979") == []

    # but if you check before it was deleted then it has children

    assert db.get_children("188979", as_of=datetime.strptime("2014-08-02", "%Y-%m-%d")) == [
        {
            "event_name": "create",
            "name": "Gyromitus sp. HFCC94",
            "parent_id": 188979,
            "rank": "species",
            "tax_id": 352463,
            "version_date": datetime(2014, 8, 1, 0, 0),
        },
    ]


@pytest.mark.parametrize(
    ["tax_id", "timestamp", "expected_names"],
    [
        (
            "1",
            datetime(2014, 9, 1, 0, 0),
            {
                "Viroids",
                "Viruses",
                "cellular organisms",
                "other sequences",
                "unclassified sequences",
            },
        ),
        (
            "1",
            datetime(2019, 5, 1, 0, 0),
            {
                #                "Viroids", # deleted
                "Viruses",
                "cellular organisms",
                "other sequences",
                "unclassified sequences",
            },
        ),
        (
            "325061",
            datetime(2014, 12, 1, 0, 0),
            {
                "Protacanthamoeba bohemica",
                "Protacanthamoeba cf. bohemica",
                "Protacanthamoeba sp. GERE3",
                "Protacanthamoeba sp. VD-2014",
            },
        ),
    ],
)
def test_children_deleted(db, tax_id, timestamp, expected_names):
    """some example cases where a node was deleted"""
    children = db.get_children(tax_id, as_of=timestamp)
    children_names = {n["name"] for n in children}
    assert children_names == expected_names


def test_get_children_moved_node(db):
    # currently, this node has no children because it was deleted
    events = db.get_events("981321")

    assert len(events) == 2
    assert events[0]["event_name"] == "create"
    assert events[1]["event_name"] == "alter"
    assert events[1]["parent_id"] == 1538467

    assert len(db.get_children("188956", as_of=datetime(2014, 9, 1, 0, 0))) == 89


def test_search_names_special_characters(db):
    matches = db.search_names("/1985", limit=10)
    assert len(matches) == 4


def test_get_events(db):
    events = db.get_events("498019")
    assert events


# TODO: there is a bug where we sometimes fetch irrelevant events
def test_get_all_events_recursive(db):
    events = db.get_all_events_recursive("498019")

    assert events


def test_get_versions(db):
    versions = db.get_versions("498019")
    assert versions

    lineages = []

    for version in versions:
        events = db.get_lineage(tax_id="498019", as_of=version)

        lineage_data = tuple([(e["rank"], e["tax_id"], e["parent_id"], e["name"]) for e in events])

        lineages.append(lineage_data)

    # no lineages should be repeated
    assert len(lineages) == len(set(lineages))


def test_get_children(db):
    events = db.get_children(tax_id="821")

    assert events

    # each tax ID should only appear once
    assert len({e["tax_id"] for e in events}) == len(events)

    events = db.get_children(tax_id="821", as_of=datetime.strptime("2015-01-01", "%Y-%m-%d"))
    assert events

    # each tax ID should only appear once
    assert len({e["tax_id"] for e in events}) == len(events)


def test_lineage(db):
    events = db.get_lineage(tax_id=821)

    assert [x["name"] for x in events] == [
        "Phocaeicola vulgatus",
        "Phocaeicola",
        "Bacteroidaceae",
        "Bacteroidales",
        "Bacteroidia",
        "Bacteroidota",
        "Bacteroidota/Chlorobiota group",
        "FCB group",
        "Bacteria",
        "cellular organisms",
    ]

    events = db.get_lineage(tax_id=821, as_of=datetime.strptime("2015-01-01", "%Y-%m-%d"))

    assert [x["name"] for x in events] == [
        "Bacteroides vulgatus",
        "Bacteroides",
        "Bacteroidaceae",
        "Bacteroidales",
        "Bacteroidia",
        "Bacteroidetes",
        "Bacteroidetes/Chlorobi group",
        "Bacteria",
        "cellular organisms",
    ]
