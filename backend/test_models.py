import pytest

from models import Taxonomy
from datetime import datetime


@pytest.fixture
def db():
    return Taxonomy(database_path="events.db")


def test_merged(db):
    pass


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


def test_search_names_special_characters(db):
    matches = db.search_names("/1985", limit=10)

    assert matches == []


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
    events = db.get_children(tax_id=821)

    assert events

    # each tax ID should only appear once
    assert len({e["tax_id"] for e in events}) == len(events)

    events = db.get_children(tax_id=821, as_of=datetime.strptime("2015-01-01", "%Y-%m-%d"))
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
