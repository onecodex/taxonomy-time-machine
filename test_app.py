import pytest

from app import Db
from datetime import datetime


@pytest.fixture
def db():
    return Db()


def test_get_children(db):
    events = db.get_children(tax_id=821)

    assert len(events) == 14

    # each tax ID should only appear once
    assert len({e["tax_id"] for e in events}) == len(events)

    events = db.get_children(tax_id=821, as_of=datetime.strptime("2015-01-01", "%Y-%m-%d"))
    assert len(events) == 13

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
