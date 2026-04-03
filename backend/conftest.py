import sqlite3
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from taxonomy_time_machine.models import Base, Taxonomy, TaxonomySource
from taxonomy_time_machine.time_machine import TimeMachine

D1 = datetime(2014, 8, 1)
D2 = datetime(2014, 9, 1)
D3 = datetime(2019, 5, 1)
D4 = datetime(2024, 12, 11)

# Minimal dataset covering: search, deletion, moves, renames, lineage changes
EVENTS = [
    # Root
    {
        "tax_id": "1",
        "name": "root",
        "parent_id": None,
        "rank": "no rank",
        "event_name": "create",
        "version_date": D1,
    },
    # Bacteria superkingdom
    {
        "tax_id": "2",
        "name": "Bacteria",
        "parent_id": "1",
        "rank": "superkingdom",
        "event_name": "create",
        "version_date": D1,
    },
    # Bacteroidetes phylum — renamed to Bacteroidota at D3
    {
        "tax_id": "10",
        "name": "Bacteroidetes",
        "parent_id": "2",
        "rank": "phylum",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "10",
        "name": "Bacteroidota",
        "parent_id": "2",
        "rank": "phylum",
        "event_name": "alter",
        "version_date": D3,
    },
    # Bacteroides genus
    {
        "tax_id": "100",
        "name": "Bacteroides",
        "parent_id": "10",
        "rank": "genus",
        "event_name": "create",
        "version_date": D1,
    },
    # Bacteroides vulgatus — renamed to Phocaeicola vulgatus at D4
    {
        "tax_id": "821",
        "name": "Bacteroides vulgatus",
        "parent_id": "100",
        "rank": "species",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "821",
        "name": "Phocaeicola vulgatus",
        "parent_id": "100",
        "rank": "species",
        "event_name": "alter",
        "version_date": D4,
    },
    # Eukaryota superkingdom
    {
        "tax_id": "3",
        "name": "Eukaryota",
        "parent_id": "1",
        "rank": "superkingdom",
        "event_name": "create",
        "version_date": D1,
    },
    # Saccharomyces genus + S. cerevisiae (uses real NCBI tax ID for test_search_names_numeric)
    {
        "tax_id": "200",
        "name": "Saccharomyces",
        "parent_id": "3",
        "rank": "genus",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "4932",
        "name": "Saccharomyces cerevisiae",
        "parent_id": "200",
        "rank": "species",
        "event_name": "create",
        "version_date": D1,
    },
    # Drosophila genus + two species
    {
        "tax_id": "3000",
        "name": "Drosophila",
        "parent_id": "3",
        "rank": "genus",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "7227",
        "name": "Drosophila melanogaster",
        "parent_id": "3000",
        "rank": "species",
        "event_name": "create",
        "version_date": D1,
    },
    # Drosophila simulans has two taxonomy rows (create + alter same name) — tests deduplication
    {
        "tax_id": "9999",
        "name": "Drosophila simulans",
        "parent_id": "3000",
        "rank": "species",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "9999",
        "name": "Drosophila simulans",
        "parent_id": "3000",
        "rank": "species",
        "event_name": "alter",
        "version_date": D2,
    },
    # Deleted node: 1001 created under 1000, then deleted at D2
    {
        "tax_id": "1000",
        "name": "DeletedGenus",
        "parent_id": "2",
        "rank": "genus",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "1001",
        "name": "DeletedSpecies",
        "parent_id": "1000",
        "rank": "species",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "1001",
        "name": None,
        "parent_id": "1000",
        "rank": None,
        "event_name": "delete",
        "version_date": D2,
    },
    # Rename of DeletedGenus *after* its child was deleted — should not appear in child's versions
    {
        "tax_id": "1000",
        "name": "RenamedDeletedGenus",
        "parent_id": "2",
        "rank": "genus",
        "event_name": "alter",
        "version_date": D3,
    },
    # Moved node: 2002 created under 2000, then moved to 2001 at D2
    {
        "tax_id": "2000",
        "name": "OriginalParent",
        "parent_id": "2",
        "rank": "genus",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "2001",
        "name": "NewParent",
        "parent_id": "2",
        "rank": "genus",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "2002",
        "name": "MovedSpecies",
        "parent_id": "2000",
        "rank": "species",
        "event_name": "create",
        "version_date": D1,
    },
    {
        "tax_id": "2002",
        "name": "MovedSpecies",
        "parent_id": "2001",
        "rank": "species",
        "event_name": "alter",
        "version_date": D2,
    },
    # Name with brackets — tests FTS special-character handling
    {
        "tax_id": "5000",
        "name": "[Candida] auris",
        "parent_id": "3",
        "rank": "species",
        "event_name": "create",
        "version_date": D1,
    },
]


@pytest.fixture(scope="session")
def db():
    # Single raw connection shared between SQLAlchemy (for setup) and TimeMachine (for queries)
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row

    engine = create_engine(
        "sqlite://",
        creator=lambda: raw_conn,
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    with Session() as session:
        source = TaxonomySource(path="test-fixture", version_date=D1)
        session.add(source)
        session.flush()
        for event in EVENTS:
            session.add(Taxonomy(taxonomy_source_id=source.id, **event))
        session.commit()

    with engine.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE name_fts USING fts5(name)"))
        conn.execute(
            text(
                "INSERT INTO name_fts(name) SELECT DISTINCT name FROM taxonomy WHERE name IS NOT NULL"
            )
        )
        conn.commit()

    tm = TimeMachine.__new__(TimeMachine)
    tm.conn = raw_conn
    tm.cursor = raw_conn.cursor()
    return tm
