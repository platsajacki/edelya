from dataclasses import dataclass
from typing import ClassVar

from rest_framework.response import Response

from apps.dishes.api.serializers.ai_drafts import DishAIDraftSerializer
from apps.dishes.api.services.ai_draft_service import AIDraftService


@dataclass
class AIDraftPayloadUpdater(AIDraftService):
    not_parsed_message: ClassVar[str] = 'AI draft can be edited only in the parsed status.'

    def act(self) -> Response:
        self.draft.payload = self.validated_data['payload']
        self.draft.save(update_fields=['payload', 'updated_at'])
        return Response(DishAIDraftSerializer(self.draft, context=self.serializer.context).data)
