from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Optional
from uuid import uuid4
import itertools

@dataclass
class ResolutionConfiguration:
    entity_type: str
    keys: List[List[str]]

@dataclass
class Record:
    id: str

    def to_keys(self, patterns: List[List[str]]) -> Dict[str, str]:
        attrs = asdict(self)
        keys: Dict[str, str] = {}
        for pattern in patterns:
            values: List[str] = []
            for attr in pattern:
                val = attrs.get(attr)
                if not val:
                    break
                values.append(val.strip().lower())
            else:
                key_name = "_".join(pattern)
                key_val = "¬".join(values)
                keys[key_name] = key_val
        return keys

@dataclass
class Individual(Record):
    prefix: Optional[str]
    first_name: Optional[str]
    middle_name: Optional[str]
    last_name: Optional[str]
    suffix: Optional[str]
    birth_date: Optional[str]

@dataclass
class Entity:
    id: str
    record_ids: Set[str]
    attrs: Dict[str, Set[str]]

@dataclass
class ResolverState:
    entities: Dict[str, Entity]
    key_index: Dict[str, str]
    dsu_parent: Dict[str, str]


def find_root(state: ResolverState, eid: str) -> str:
    parent = state.dsu_parent
    while parent[eid] != eid:
        parent[eid] = parent[parent[eid]]
        eid = parent[eid]
    return eid


def fuse_attrs(target: Entity, other: Entity) -> None:
    target.record_ids |= other.record_ids
    for attr, vals in other.attrs.items():
        if attr in target.attrs:
            target.attrs[attr].update(vals)
        else:
            target.attrs[attr] = set(vals)


def union(state: ResolverState, a: str, b: str) -> None:
    ra = find_root(state, a)
    rb = find_root(state, b)
    if ra == rb:
        return
    state.dsu_parent[rb] = ra
    fuse_attrs(state.entities[ra], state.entities[rb])
    del state.entities[rb]


def new_entity(rec: Record) -> Entity:
    eid = uuid4().hex
    raw = asdict(rec)
    attrs: Dict[str, Set[str]] = {}
    for k, v in raw.items():
        if v not in (None, ""):
            attrs[k] = {v.strip().lower()}
    return Entity(id=eid, record_ids={rec.id}, attrs=attrs)


def append_record(ent: Entity, rec: Record) -> None:
    ent.record_ids.add(rec.id)
    raw = asdict(rec)
    for k, v in raw.items():
        if v not in (None, ""):
            ent.attrs.setdefault(k, set()).add(v.strip().lower())


def build_all_keys(ent: Entity, patterns: List[List[str]]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for pattern in patterns:
        if any(attr not in ent.attrs or not ent.attrs[attr] for attr in pattern):
            continue
        for combo in itertools.product(*(ent.attrs[attr] for attr in pattern)):
            key_name = "_".join(pattern)
            key_val  = "¬".join(combo)
            result[key_name] = key_val
    return result


def lookup(state: ResolverState, key_val: str) -> Optional[str]:
    eid = state.key_index.get(key_val)
    if eid is None:
        return None
    return find_root(state, eid)


def resolve(
    cfg: ResolutionConfiguration,
    state: ResolverState,
    rec: Record
) -> str:
    # 1) build this record's blocking keys
    keys = rec.to_keys(cfg.keys)

    # 2) find all matching entity roots
    roots: Set[str] = set()
    for val in keys.values():
        r = lookup(state, val)
        if r is not None:
            roots.add(r)

    # 3) if nothing matches, create a new entity
    if not roots:
        ent = new_entity(rec)
        state.entities[ent.id]   = ent
        state.dsu_parent[ent.id] = ent.id
        # index all record keys
        for val in keys.values():
            state.key_index[val] = ent.id
        return ent.id

    # 4) choose one root and merge others into it
    root = min(roots)
    for other in roots - {root}:
        union(state, root, other)

    # 5) attach this record to the surviving entity
    append_record(state.entities[root], rec)

    # 6) now handle transitive merges via new composite keys
    while True:
        composite = build_all_keys(state.entities[root], cfg.keys)
        more: Set[str] = set()
        for val in composite.values():
            if val in state.key_index:
                other = find_root(state, state.key_index[val])
                if other != root:
                    more.add(other)
        if not more:
            break
        for other in more:
            union(state, root, other)

    # 7) finally index any composite keys not yet seen
    composite = build_all_keys(state.entities[root], cfg.keys)
    for val in composite.values():
        state.key_index.setdefault(val, root)

    return root
