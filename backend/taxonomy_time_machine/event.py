from datetime import datetime

from dataclasses import dataclass
from enum import Enum


class EventName(Enum):
    Create = "create"
    Delete = "delete"
    Update = "alter"  # TODO: change me to Update


# TODO: encode what changed using a bitarray
@dataclass
class Event:
    event_name: EventName
    tax_id: str
    version_date: datetime
    taxonomy_source_id: int
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
            taxonomy_source_id=data["taxonomy_source_id"],
        )

    def to_dict(self) -> dict:
        return {
            "event_name": self.event_name.value,
            "version_date": self.version_date,
            "tax_id": self.tax_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "rank": self.rank,
            "taxonomy_source_id": self.taxonomy_source_id,
        }
