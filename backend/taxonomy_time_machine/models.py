from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TaxonomySource(Base):
    __tablename__ = "taxonomy_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(Text)
    version_date: Mapped[datetime] = mapped_column(DateTime)

    # Relationship to taxonomy records
    taxonomy_records: Mapped[list["Taxonomy"]] = relationship(back_populates="source")


class Taxonomy(Base):
    __tablename__ = "taxonomy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    taxonomy_source_id: Mapped[int] = mapped_column(Integer, ForeignKey("taxonomy_source.id"))
    event_name: Mapped[str] = mapped_column(Text)
    version_date: Mapped[datetime] = mapped_column(DateTime)
    tax_id: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    rank: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship to source
    source: Mapped[TaxonomySource] = relationship(back_populates="taxonomy_records")


def create_db_engine(database_path: str):
    """Create SQLAlchemy engine for the given database path"""
    return create_engine(f"sqlite:///{database_path}")
