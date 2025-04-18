from dataclasses import dataclass


@dataclass
class ResolutionConfiguration:
    entity_type: str
    keys: list[list[str]]



