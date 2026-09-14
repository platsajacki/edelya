import pytest

from typing import Any

from django.conf import settings

from _tests import FixtureFactory

IP_HEADER = 'HTTP_X_REAL_IP'


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db: Any) -> None:
    pass


@pytest.fixture(autouse=True)
def configure_ip_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, 'IP_HEADER', IP_HEADER)


pytest_plugins = [
    '_tests.fixtures.dishes',
    '_tests.fixtures.ingredients',
    '_tests.fixtures.main',
    '_tests.fixtures.marketing',
    '_tests.fixtures.mocks',
    '_tests.fixtures.planning',
    '_tests.fixtures.shopping',
    '_tests.fixtures.subscriptions',
    '_tests.fixtures.users',
]


@pytest.fixture
def factory() -> FixtureFactory:
    return FixtureFactory()
