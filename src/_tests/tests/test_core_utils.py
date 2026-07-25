import pytest

from django.http import HttpRequest
from rest_framework.request import Request

from _tests.conftest import IP_HEADER
from core.utils import get_client_ip


def make_request(meta: dict[str, str]) -> Request:
    django_request = HttpRequest()
    django_request.META = meta
    return Request(django_request)


class TestGetClientIp:
    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            (' 192.0.2.1 ', '192.0.2.1'),
            ('2001:0db8:0000:0000:0000:ff00:0042:8329', '2001:db8::ff00:42:8329'),
        ],
    )
    def test_returns_normalized_ip_from_configured_header(self, value: str, expected: str) -> None:
        request = make_request({IP_HEADER: value})
        assert get_client_ip(request) == expected

    def test_configured_header_takes_precedence_over_remote_address(self) -> None:
        request = make_request(
            {
                IP_HEADER: '198.51.100.10',
                'REMOTE_ADDR': '192.0.2.1',
            }
        )
        assert get_client_ip(request) == '198.51.100.10'

    @pytest.mark.parametrize('header_value', [None, ''])
    def test_falls_back_to_remote_address_when_header_is_missing_or_empty(self, header_value: str | None) -> None:
        meta = {'REMOTE_ADDR': ' 203.0.113.5 '}
        if header_value is not None:
            meta[IP_HEADER] = header_value
        request = make_request(meta)
        assert get_client_ip(request) == '203.0.113.5'

    def test_returns_none_when_ip_is_missing(self) -> None:
        assert get_client_ip(make_request({})) is None

    @pytest.mark.parametrize(
        'meta',
        [
            {IP_HEADER: 'not-an-ip'},
            {'REMOTE_ADDR': '999.999.999.999'},
        ],
    )
    def test_returns_none_for_invalid_ip(self, meta: dict[str, str]) -> None:
        assert get_client_ip(make_request(meta)) is None

    def test_does_not_fall_back_when_configured_header_is_invalid(self) -> None:
        request = make_request(
            {
                IP_HEADER: 'not-an-ip',
                'REMOTE_ADDR': '192.0.2.1',
            }
        )
        assert get_client_ip(request) is None
