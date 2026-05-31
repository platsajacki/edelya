from typing import TYPE_CHECKING

from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.settings.models import Prompt  # noqa: F401


class PromptQuerySet(BaseQuerySet['Prompt']): ...


class PromptManager(BaseManager['Prompt', PromptQuerySet]):
    def get_queryset_class(self) -> type[PromptQuerySet]:
        return PromptQuerySet
