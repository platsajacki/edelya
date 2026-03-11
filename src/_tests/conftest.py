import pytest

from typing import Any

from _tests import FixtureFactory


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db: Any) -> None:
    pass


pytest_plugins = [
    '_tests.fixtures.dishes',
    '_tests.fixtures.ingredients',
    '_tests.fixtures.main',
    '_tests.fixtures.mocks',
    '_tests.fixtures.planning',
    '_tests.fixtures.users',
]


@pytest.fixture
def factory() -> FixtureFactory:
    return FixtureFactory()
