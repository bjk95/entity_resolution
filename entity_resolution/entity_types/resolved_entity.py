from dataclasses import dataclass


@dataclass
class ResolvedEntity:
    id: str
    entity_type: str
    record_ids: set[str]            # original record ids
    attrs: dict[str, set[str]]      # { "first_name": {"brad"}, ...}