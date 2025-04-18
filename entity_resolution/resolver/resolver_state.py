from dataclasses import dataclass

from entity_resolution.entity_types.resolved_entity import ResolvedEntity



@dataclass
class ResolverState:
    entities: dict[str, ResolvedEntity]     # EntityId → Entity
    key_index: dict[str, str]       # key string → EntityId
    dsu_parent: dict[str, str]      # for quick union‑find (optional)