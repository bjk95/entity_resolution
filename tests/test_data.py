
from entity_resolution.entity_types.individual import Individual


test_individual_1 = Individual(
    id="1",
    prefix="",
    first_name="Brad",
    middle_name="",
    last_name="Pitt",
    suffix="",
    birth_date="1963-12-18",
)

test_individual_2 = Individual(
    id="2",
    prefix="",
    first_name="Brad",
    middle_name="",
    last_name="Pitt",
    suffix="",
    birth_date="1963-12-18",
)

test_individual_3 = Individual(
    id="3",
    prefix="",
    first_name="Brad",
    middle_name="james",
    last_name="Kester",
    suffix="",
    birth_date="1995-05-30",
)

test_individual_4 = Individual(
    id="4",
    prefix="",
    first_name="Bradley",
    middle_name="James",
    last_name="Kester",
    suffix="",
    birth_date="1995-05-30",
)

test_individuals = [
    test_individual_1,
    test_individual_2,
    test_individual_3,
    test_individual_4,
]
