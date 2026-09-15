from django.conf import settings

from openai import DefaultHttpxClient, OpenAI

openai_client = OpenAI(
    http_client=DefaultHttpxClient(proxy=settings.OPENAI_PROXY_URL if settings.OPENAI_PROXY_URL else None),
    timeout=settings.OPENAI_TIMEOUT_SEC,
    max_retries=0,
)
