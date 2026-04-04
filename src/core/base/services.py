from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

from django.db.models import Model, QuerySet
from rest_framework.serializers import BaseSerializer


class BaseService(metaclass=ABCMeta):
    def __call__(self) -> Any:
        self.validate()
        return self.act()

    def get_log_msg(self, message: str) -> str:
        return f'[{self.__repr__()}] {message}'

    def get_validators(self) -> list[Callable]:
        return []

    def validate(self) -> None:
        validators = self.get_validators()
        for validator in validators:
            validator()

    @abstractmethod
    def act(self) -> Any:
        raise NotImplementedError('Please implement in the services class')


@dataclass
class BaseViewSetService(BaseService):
    serializer: BaseSerializer
    raise_exception: bool = dc_field(default=True)
    validated_data: dict = dc_field(init=False, repr=False)

    def validate_serializer(self) -> None:
        self.serializer.is_valid(raise_exception=self.raise_exception)
        self.validated_data = self.serializer.validated_data

    def get_validators(self) -> list[Callable]:
        return super().get_validators() + [self.validate_serializer]


@dataclass
class BaseViewSetPerformService(BaseService):
    serializer: BaseSerializer


@dataclass
class BaseInstanceService(BaseService):
    instance: Model


@dataclass
class PerformActionInstanceRefresher(BaseViewSetPerformService):
    qs: QuerySet

    def act(self) -> Model:
        instance = self.serializer.save()
        return self.qs.get(pk=instance.pk)
