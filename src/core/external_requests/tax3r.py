from dataclasses import asdict, dataclass
from dataclasses import field as dc_field

from django.conf import settings

from requests import Response

from core.external_requests import requests_session


@dataclass
class TaxCheckData:
    service_name: str
    price: str
    payment_id: str
    service: str = dc_field(default=settings.SERVICE_NAME)


def send_payment_check_to_taxer(data: TaxCheckData) -> Response:
    url = f'{settings.TAX3R_URL.rstrip("/")}/send_check'
    headers = {'x-api-key': settings.TAX3R_API_KEY}
    return requests_session.post(url, json=asdict(data), headers=headers, timeout=10)
