from dataclasses import asdict, dataclass

from django.conf import settings

import requests


@dataclass
class TaxCheckData:
    service_name: str
    price: str
    payment_id: str


def send_payment_check_to_taxer(data: TaxCheckData) -> requests.Response:
    url = f'{settings.TAX3R_URL.rstrip("/")}/send_check'
    headers = {'x-api-key': settings.TAX3R_API_KEY}
    return requests.post(url, json=asdict(data), headers=headers, timeout=10)
