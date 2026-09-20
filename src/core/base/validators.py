from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db.models import Model, Q, QuerySet
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import BaseSerializer

_ExpressionFieldType = str
_SequenceOfExpressionFieldType = list[_ExpressionFieldType] | tuple[_ExpressionFieldType, ...]

ALLOWED_OPERATORS = {'iexact'}


class UniqueTogetherWithOperatorValidator:
    requires_context = True

    def __init__(
        self, queryset: QuerySet, fields: _SequenceOfExpressionFieldType, message: str, condition: Q | None = None
    ) -> None:
        self.queryset = queryset
        self.fields = fields
        self.message = message
        self.condition = condition

    def get_field_operator(self, field: _ExpressionFieldType) -> tuple[str, str | None]:
        if any(field.endswith(f'__{op}') for op in ALLOWED_OPERATORS):
            field_name, operator = field.rsplit('__', 1)
            return field_name, operator
        return field, None

    def get_field_value(self, field_name: str, attrs: dict, instance: Model | None) -> Any:
        value = attrs.get(field_name)
        if value is None and instance is not None:
            return getattr(instance, field_name, None)
        return value

    def create_filter_kwargs(self, attrs: dict, instance: Model | None) -> dict:
        filter_kwargs = {}
        for field in self.fields:
            field_name, operator = self.get_field_operator(field)
            value = self.get_field_value(field_name, attrs, instance)
            if value is None:
                continue
            filter_key = f'{field_name}__{operator}' if operator else field_name
            filter_kwargs[filter_key] = value
        return filter_kwargs

    def create_queryset(self, instance: Model | None) -> QuerySet:
        queryset = self.queryset if self.condition is None else self.queryset.filter(self.condition)
        return queryset if instance is None else queryset.exclude(pk=instance.pk)

    def __call__(self, attrs: dict, serializer: BaseSerializer) -> None:
        instance = getattr(serializer, 'instance', None)
        filter_kwargs = self.create_filter_kwargs(attrs, instance)
        if not filter_kwargs:
            return
        if self.create_queryset(instance).filter(**filter_kwargs).exists():
            raise ValidationError(self.message)


class HexColorValidator(RegexValidator):
    regex = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    message = 'Enter a valid hex color code (e.g., #RRGGBB or #RGB).'
    flags = 0


def dict_validator(
    value: dict, error_type: type[DjangoValidationError] | type[ValidationError] = DjangoValidationError
) -> None:
    if not isinstance(value, dict):
        raise error_type('Value must be a dictionary.')


def validate_balanced_braces(value: str) -> None:
    open_count = value.count('{')
    close_count = value.count('}')
    if open_count != close_count:
        raise ValidationError('The number of opening and closing braces must be the same.')
