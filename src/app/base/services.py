from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import Any


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
