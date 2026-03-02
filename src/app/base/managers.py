from abc import abstractmethod
from typing import Self

from django.db.models import Manager, Model, QuerySet


class BaseQuerySet[ModelType: Model](QuerySet[ModelType]): ...


class BaseManager[ModelType: Model, QuerySetType: BaseQuerySet](Manager[ModelType]):
    @abstractmethod
    def get_queryset_class(self) -> type[QuerySetType]:
        raise NotImplementedError('Subclasses must implement get_queryset_class method')

    def get_queryset(self) -> QuerySetType:
        queryset_class = self.get_queryset_class()
        return queryset_class(self.model, using=self._db)


class ActiveQuerySet[ModelType: Model](BaseQuerySet[ModelType]):
    def actived(self) -> Self:
        return self.filter(is_active=True)


class ActiveManager[ModelType: Model, QuerySetType: ActiveQuerySet](BaseManager[ModelType, QuerySetType]):
    def actived(self) -> QuerySetType:
        return self.get_queryset().actived()
