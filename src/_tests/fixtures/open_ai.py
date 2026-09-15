import pytest

import httpx
from openai import APIConnectionError, BadRequestError, InternalServerError, RateLimitError

_OPENAI_URL = 'https://api.openai.com/v1/chat/completions'


class OpenAIErrorFactory:
    def __init__(self) -> None:
        self.request = httpx.Request('POST', _OPENAI_URL)

    def _response(self, status_code: int, headers: dict[str, str] | None = None) -> httpx.Response:
        return httpx.Response(status_code, headers=headers, request=self.request)

    def rate_limit(
        self,
        code: str = 'rate_limit_exceeded',
        message: str = 'Rate limit reached.',
        headers: dict[str, str] | None = None,
    ) -> RateLimitError:
        return RateLimitError(message, response=self._response(429, headers), body={'code': code})

    def server_error(self) -> InternalServerError:
        return InternalServerError('Server error.', response=self._response(500), body=None)

    def bad_request(self) -> BadRequestError:
        return BadRequestError('Bad request.', response=self._response(400), body=None)

    def connection_error(self) -> APIConnectionError:
        return APIConnectionError(request=self.request)


@pytest.fixture
def openai_error_factory() -> OpenAIErrorFactory:
    return OpenAIErrorFactory()
