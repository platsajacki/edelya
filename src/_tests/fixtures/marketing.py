import pytest

from typing import Any

from apps.marketing.models.model_enums import MessageTemplateName
from apps.marketing.models.template_messages import MessageTemplate


@pytest.fixture(autouse=True)
def message_templates(db: Any) -> list[MessageTemplate]:
    return MessageTemplate.objects.bulk_create(
        [
            MessageTemplate(
                name=name,
                text_str=name.label,
                with_variables=True,
            )
            for name in MessageTemplateName
        ]
    )
