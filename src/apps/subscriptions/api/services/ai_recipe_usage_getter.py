from dataclasses import dataclass

from rest_framework.response import Response

from apps.dishes.api.services.ai_draft_usage import AIDraftUsageCalculator
from apps.subscriptions.api.serializers.subscriptions import AIRecipeUsageSerializer
from apps.subscriptions.api.services.base import CurrentSubscriptionService


@dataclass
class AIRecipeUsageGetter(CurrentSubscriptionService):
    def act(self) -> Response:
        usage = AIDraftUsageCalculator(subscription=self.subscription)()
        serializer = AIRecipeUsageSerializer(usage.to_dict())
        return Response(serializer.data)
