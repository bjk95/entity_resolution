import pytest
from entity_resolution.resolver.resolver import (
    ResolutionConfiguration,
    Individual,
    ResolverState,
    resolve,
    find_root,
    lookup
)

@pytest.fixture
def cfg():
    return ResolutionConfiguration(
        entity_type="individual",
        keys=[
            ["first_name", "last_name", "birth_date"],
            ["middle_name", "last_name", "birth_date"],
            ["first_name", "birth_date"]
        ]
    )

@pytest.fixture
def fresh_state():
    return ResolverState(entities={}, key_index={}, dsu_parent={})


def make_ind(rec_id, first, middle, last, dob):
    return Individual(
        id=rec_id,
        prefix=None,
        first_name=first,
        middle_name=middle,
        last_name=last,
        suffix=None,
        birth_date=dob
    )


def test_single_record_creates_entity(cfg, fresh_state):
    rec = make_ind("r1", "Alice", None, "Smith", "1990-01-01")
    eid = resolve(cfg, fresh_state, rec)
    ent = fresh_state.entities[eid]
    assert ent.record_ids == {"r1"}
    assert ent.attrs["first_name"] == {"alice"}
    assert ent.attrs["last_name"] == {"smith"}
    key = "alice¬smith¬1990-01-01"
    assert lookup(fresh_state, key) == eid


def test_no_match_creates_two_entities(cfg, fresh_state):
    r1 = make_ind("r1", "John", None, "Doe", "1980-05-05")
    r2 = make_ind("r2", "John", None, "Doe", "1981-05-05")
    id1 = resolve(cfg, fresh_state, r1)
    id2 = resolve(cfg, fresh_state, r2)
    assert id1 != id2
    assert len(fresh_state.entities) == 2


def test_simple_merge_on_first_and_dob(cfg, fresh_state):
    r1 = make_ind("r1", "Bob", None, None, "1970-07-07")
    r2 = make_ind("r2", "Bob", None, None, "1970-07-07")
    id1 = resolve(cfg, fresh_state, r1)
    id2 = resolve(cfg, fresh_state, r2)
    assert id1 == id2
    ent = fresh_state.entities[id1]
    assert ent.record_ids == {"r1", "r2"}


def test_transitive_merge(cfg, fresh_state):
    A = make_ind("A", "Brad", None, "Pitt", "1963")
    C = make_ind("C", None, "William", "Pitt", "1963")
    B = make_ind("B", "Brad", "William", None, "1963")
    idA = resolve(cfg, fresh_state, A)
    idC = resolve(cfg, fresh_state, C)
    assert idA != idC
    idB = resolve(cfg, fresh_state, B)
    roots = {find_root(fresh_state, x) for x in (idA, idB, idC)}
    assert len(roots) == 1


def test_lookup_returns_entity_ids(cfg, fresh_state):
    r1 = make_ind("r1", "Sam", None, "Jones", "1985-08-08")
    r2 = make_ind("r2", None, "Timothy", "Jones", "1985-08-08")
    id1 = resolve(cfg, fresh_state, r1)
    id2 = resolve(cfg, fresh_state, r2)
    key1 = "sam¬jones¬1985-08-08"
    key2 = "timothy¬jones¬1985-08-08"
    assert lookup(fresh_state, key1) == id1
    assert lookup(fresh_state, key2) == id2


def test_idempotent_resolve(cfg, fresh_state):
    r = make_ind("r1", "Eve", None, "Adams", "1992-02-02")
    id1 = resolve(cfg, fresh_state, r)
    id2 = resolve(cfg, fresh_state, r)
    assert id1 == id2
    assert len(fresh_state.entities) == 1

# Edge-case tests

def test_missing_attributes_no_keys(cfg, fresh_state):
    r = make_ind("r_missing", None, None, None, None)
    eid = resolve(cfg, fresh_state, r)
    assert eid in fresh_state.entities
    # no composite keys should be indexed
    assert fresh_state.key_index == {}


def test_whitespace_and_case_normalization(cfg, fresh_state):
    r1 = make_ind("r1", "  Alice  ", None, "SMITH", "1990-01-01")
    eid1 = resolve(cfg, fresh_state, r1)
    # normalized lookup
    key = "alice¬smith¬1990-01-01"
    assert lookup(fresh_state, key) == eid1
    # resolve duplicate with different casing/whitespace
    r2 = make_ind("r1_dup", "ALICE", None, " smith ", "1990-01-01")
    eid2 = resolve(cfg, fresh_state, r2)
    assert eid2 == eid1
    ent = fresh_state.entities[eid1]
    assert ent.record_ids == {"r1", "r1_dup"}


def test_partial_key_no_merge_unless_pattern(cfg, fresh_state):
    # only last_name+dob, but no pattern covers that exactly
    r1 = make_ind("r1", None, None, "Jones", "1980-01-01")
    r2 = make_ind("r2", None, None, "Jones", "1980-01-01")
    id1 = resolve(cfg, fresh_state, r1)
    id2 = resolve(cfg, fresh_state, r2)
    assert id1 != id2


def test_chain_of_merges(cfg, fresh_state):
    # r1: John Doe 1970 → creates E1
    # r2: None Michael Doe 1970 → creates E2
    # r3: John None None 1970 → merges into E1 only
    r1 = make_ind("r1", "John", None, "Doe", "1970-01-01")
    r2 = make_ind("r2", None, "Michael", "Doe", "1970-01-01")
    r3 = make_ind("r3", "John", None, None, "1970-01-01")

    id1 = resolve(cfg, fresh_state, r1)
    id2 = resolve(cfg, fresh_state, r2)
    # initially two separate entities
    assert find_root(fresh_state, id1) != find_root(fresh_state, id2)

    id3 = resolve(cfg, fresh_state, r3)
    # r3 should merge into E1, not E2
    root1 = find_root(fresh_state, id1)
    root2 = find_root(fresh_state, id2)
    root3 = find_root(fresh_state, id3)

    assert root3 == root1
    assert root2 != root1
    # overall there should remain two entities
    roots = {root1, root2}
    assert len(roots) == 2