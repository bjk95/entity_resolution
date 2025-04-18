import pytest
from entity_resolution.entity_types.individual import Individual
from entity_resolution.resolver.resolution_configuration import ResolutionConfiguration
from entity_resolution.resolver.resolver import find_root, resolve
from entity_resolution.resolver.resolver_state import ResolverState


@ pytest.fixture
def cfg():
    # define the matching keys for individuals
    return ResolutionConfiguration(
        entity_type="individual",
        keys=[
            ["first_name", "last_name", "birth_date"],
            ["middle_name", "last_name", "birth_date"],
            ["first_name", "birth_date"]
        ]
    )

@ pytest.fixture
def fresh_state():
    # start with an empty resolver state
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


def test_single_record_creates_new_entity(cfg, fresh_state):
    rec = make_ind("r1", "Alice", None, "Smith", "1990-01-01")
    eid = resolve(cfg, fresh_state, rec)

    # the entity should exist and include our record
    assert eid in fresh_state.entities
    ent = fresh_state.entities[eid]
    assert ent.record_ids == {"r1"}
    # attributes should be stored
    assert ent.attrs["first_name"] == {"Alice"}
    assert ent.attrs["last_name"] == {"Smith"}
    assert ent.attrs["birth_date"] == {"1990-01-01"}


def test_no_match_creates_two_entities(cfg, fresh_state):
    rec1 = make_ind("r1", "John", None, "Doe", "1980-05-05")
    rec2 = make_ind("r2", "Jane", None, "Doe", "1980-05-06")

    id1 = resolve(cfg, fresh_state, rec1)
    id2 = resolve(cfg, fresh_state, rec2)

    # different birth dates → separate entities
    assert id1 != id2
    assert len(fresh_state.entities) == 2


def test_simple_merge_on_first_and_dob(cfg, fresh_state):
    rec1 = make_ind("r1", "Bob", None, None, "1970-07-07")
    rec2 = make_ind("r2", "Bob", None, None, "1970-07-07")

    id1 = resolve(cfg, fresh_state, rec1)
    id2 = resolve(cfg, fresh_state, rec2)

    # they match on first_name+birth_date
    assert id1 == id2
    ent = fresh_state.entities[id1]
    assert ent.record_ids == {"r1", "r2"}


def test_transitive_merge_three_records(cfg, fresh_state):
    # A: Brad Pitt 1963
    recA = make_ind("A", "Brad", None, "Pitt", "1963")
    # C: None William Pitt 1963 (middle+last+dob)
    recC = make_ind("C", None, "William", "Pitt", "1963")
    # B: Brad William None 1963 (first+dob and middle+last+dob)
    recB = make_ind("B", "Brad", "William", None, "1963")

    idA = resolve(cfg, fresh_state, recA)
    idC = resolve(cfg, fresh_state, recC)
    # initially separated
    assert idA != idC

    idB = resolve(cfg, fresh_state, recB)
    # all three should now be in the same entity
    roots = { find_root(fresh_state, eid) for eid in [idA, idB, idC] }
    assert len(roots) == 1

    root = roots.pop()
    ent = fresh_state.entities[root]
    assert ent.record_ids == {"A", "B", "C"}
    # fused attributes include all non-null values
    assert ent.attrs["first_name"] == {"Brad"}
    assert ent.attrs["middle_name"] == {"William"}
    assert ent.attrs["last_name"] == {"Pitt"}
    assert ent.attrs["birth_date"] == {"1963"}


def test_index_keys_updated_after_merge(cfg, fresh_state):
    rec1 = make_ind("r1", "Sam", None, "Jones", "1985-08-08")
    rec2 = make_ind("r2", None, "Timothy", "Jones", "1985-08-08")

    id1 = resolve(cfg, fresh_state, rec1)
    id2 = resolve(cfg, fresh_state, rec2)

    # they should merge (first+dob for rec1, middle+last+dob for rec2 → new key)
    root = find_root(fresh_state, id1)
    ent = fresh_state.entities[root]

    # build expected composite key
    expected_key = "Timothy¬Jones¬1985-08-08"
    # index must map that key to our root entity
    assert fresh_state.key_index.get(expected_key) == root


