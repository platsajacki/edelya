import time

from django.conf import settings
from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper
from django.db.utils import OperationalError

import psycopg2

from core.logging_handlers import loki_logger


def check_delay_between_retries(delay: float) -> float:
    if delay < 0:
        loki_logger.warning('Negative DELAY_BETWEEN_DB_RETRIES value %s is invalid, setting to 0.2', delay)
        delay = 0.2
    if delay > 1:
        loki_logger.warning('High DELAY_BETWEEN_DB_RETRIES value %s may slow down application startup', delay)
    return delay


DELAY_BETWEEN_DB_RETRIES = check_delay_between_retries(settings.DELAY_BETWEEN_DB_RETRIES)


class DatabaseWrapper(PostgresDatabaseWrapper):
    def get_new_connection(self, conn_params: dict) -> psycopg2.extensions.connection:
        last_error: BaseException | None = None
        for attempt in range(1, settings.MAX_DB_CONNECTION_RETRIES + 1):
            try:
                return super().get_new_connection(conn_params)
            except (OperationalError, psycopg2.OperationalError) as e:
                msg = str(e)
                transient = 'Temporary failure in name resolution' in msg or 'could not connect to server' in msg
                if not transient:
                    raise
                last_error = e
                loki_logger.warning(
                    'Database connection attempt %s/%s failed: %s',
                    attempt,
                    settings.MAX_DB_CONNECTION_RETRIES,
                    msg,
                    exc_info=True,
                )
                if attempt == settings.MAX_DB_CONNECTION_RETRIES:
                    break
                time.sleep(DELAY_BETWEEN_DB_RETRIES)
        if last_error is None:
            raise OperationalError('Failed to establish a database connection after retries')
        raise last_error
