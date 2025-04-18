from dataclasses import dataclass

from entity_resolution.entity_types.record import Record


@dataclass
class Individual(Record):
    prefix: str | None
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    suffix: str | None
    birth_date: str | None
