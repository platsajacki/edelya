from dataclasses import dataclass

from rest_framework.response import Response

from apps.subscriptions.api.serializers.subscriptions import SubscriptionSerializer
from apps.subscriptions.api.services.base import CurrentSubscriptionService


@dataclass
class SubscriptionGetter(CurrentSubscriptionService):
    serializer_class: type[SubscriptionSerializer]

    def act(self) -> Response:
        serializer = self.serializer_class(self.subscription)
        return Response(serializer.data)
