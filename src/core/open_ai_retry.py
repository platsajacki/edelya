import re
from dataclasses import dataclass
from random import uniform

from openai import APIConnectionError, InternalServerError, RateLimitError

_DURATION_PATTERN = re.compile(r'(\d+(?:\.\d+)?)(ms|s|m|h)')
_DURATION_UNITS = {'ms': 0.001, 's': 1, 'm': 60, 'h': 3600}
_TRY_AGAIN_PATTERN = re.compile(r'try again in ((?:\d+(?:\.\d+)?(?:ms|s|m|h))+)')


@dataclass
class RetryAfterParser:
    error: RateLimitError

    def _parse_duration(self, value: str) -> float | None:
        matches = _DURATION_PATTERN.findall(value)
        return sum(float(amount) * _DURATION_UNITS[unit] for amount, unit in matches) if matches else None

    def _from_headers(self) -> float | None:
        headers = self.error.response.headers
        if retry_after_ms := headers.get('retry-after-ms'):
            return float(retry_after_ms) / 1000
        retry_after = headers.get('retry-after', '')
        return float(retry_after) if retry_after.replace('.', '', 1).isdigit() else None

    def _from_message(self) -> float | None:
        match = _TRY_AGAIN_PATTERN.search(self.error.message)
        return self._parse_duration(match.group(1)) if match else None

    def seconds(self) -> float | None:
        return self._from_headers() or self._from_message()


@dataclass(frozen=True)
class OpenAIRetryPolicy:
    base_delay_sec: float = 2
    max_delay_sec: float = 30
    jitter_sec: float = 1

    def _backoff(self, attempt: int) -> float:
        return self.base_delay_sec * 2**attempt

    def _rate_limit_delay(self, error: RateLimitError, attempt: int) -> float | None:
        if error.code == 'insufficient_quota':
            return None
        return RetryAfterParser(error).seconds() or self._backoff(attempt)

    def _raw_delay(self, error: Exception, attempt: int) -> float | None:
        if isinstance(error, RateLimitError):
            return self._rate_limit_delay(error, attempt)
        if isinstance(error, (APIConnectionError, InternalServerError)):
            return self._backoff(attempt)
        return None

    def get_delay(self, error: Exception, attempt: int) -> float | None:
        delay = self._raw_delay(error, attempt)
        if delay is None or delay > self.max_delay_sec:
            return None
        return round(delay + uniform(0, self.jitter_sec), 3)
