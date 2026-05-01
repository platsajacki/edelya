from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.subscriptions.services.webhook_handler import WebhookHandler
from core.logging_handlers import tg_logger


class YookassaWebhookView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        try:
            WebhookHandler(
                event=request.data.get('event', ''),
                object_data=request.data.get('object', {}),
            )()
        except Exception as e:
            tg_logger.exception('YooKassa webhook processing failed, event=%s', request.data.get('event'), exc_info=e)
        return Response(status=status.HTTP_200_OK)
