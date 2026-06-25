from typing import TYPE_CHECKING

from apps.settings.model_enums import PromptName
from core.base.managers import BaseManager, BaseQuerySet

if TYPE_CHECKING:
    from apps.settings.models import Prompt  # noqa: F401


class PromptQuerySet(BaseQuerySet['Prompt']):
    def by_name(self, name: str | PromptName) -> Prompt:
        if isinstance(name, PromptName):
            name = name.value
        return self.get(name=name)


class PromptManager(BaseManager['Prompt', PromptQuerySet]):
    def get_queryset_class(self) -> type[PromptQuerySet]:
        return PromptQuerySet

    def get_by_name(self, name: str | PromptName) -> Prompt:
        return self.get_queryset().by_name(name)
