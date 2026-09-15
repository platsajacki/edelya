import pytest

from _tests.fixtures.open_ai import OpenAIErrorFactory
from core.open_ai_retry import OpenAIRetryPolicy, RetryAfterParser


class TestRetryAfterParser:
    @pytest.mark.parametrize(
        ('headers', 'message', 'expected'),
        [
            ({'retry-after-ms': '250'}, 'Rate limit reached.', 0.25),
            ({'retry-after': '3'}, 'Rate limit reached.', 3.0),
            ({}, 'Please try again in 2.91s.', 2.91),
            ({}, 'Please try again in 1m30s.', 90.0),
            ({}, 'Please try again in 250ms.', 0.25),
            ({}, 'Rate limit reached.', None),
        ],
    )
    def test_seconds(
        self,
        headers: dict[str, str],
        message: str,
        expected: float | None,
        openai_error_factory: OpenAIErrorFactory,
    ) -> None:
        error = openai_error_factory.rate_limit(message=message, headers=headers)
        assert RetryAfterParser(error).seconds() == pytest.approx(expected)


class TestOpenAIRetryPolicy:
    def test_backoff_grows_with_attempt(self, openai_error_factory: OpenAIErrorFactory) -> None:
        policy = OpenAIRetryPolicy(jitter_sec=0)
        error = openai_error_factory.server_error()
        assert [policy.get_delay(error, attempt) for attempt in range(3)] == [2, 4, 8]

    def test_delay_above_max_is_not_retried(self, openai_error_factory: OpenAIErrorFactory) -> None:
        policy = OpenAIRetryPolicy(max_delay_sec=5)
        assert policy.get_delay(openai_error_factory.connection_error(), attempt=2) is None

    def test_rate_limit_uses_retry_after(self, openai_error_factory: OpenAIErrorFactory) -> None:
        error = openai_error_factory.rate_limit(headers={'retry-after': '7'})
        assert OpenAIRetryPolicy(jitter_sec=0).get_delay(error, attempt=0) == 7

    def test_insufficient_quota_is_not_retried(self, openai_error_factory: OpenAIErrorFactory) -> None:
        error = openai_error_factory.rate_limit(code='insufficient_quota')
        assert OpenAIRetryPolicy().get_delay(error, attempt=0) is None

    def test_non_openai_error_is_not_retried(self) -> None:
        assert OpenAIRetryPolicy().get_delay(ValueError('boom'), attempt=0) is None
