from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db.models import Q, QuerySet
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import BaseSerializer

_ExpressionFieldType = str
_SequenceOfExpressionFieldType = list[_ExpressionFieldType] | tuple[_ExpressionFieldType, ...]

ALLOWED_OPERATORS = {'iexact'}


class UniqueTogetherWithOperatorValidator:
    def __init__(
        self, queryset: QuerySet, fields: _SequenceOfExpressionFieldType, message: str, condition: Q | None = None
    ) -> None:
        self.queryset = queryset
        self.fields = fields
        self.message = message
        self.condition = condition
        self.serializer: BaseSerializer | None = None

    def get_field_operator(self, field: _ExpressionFieldType) -> tuple[str, str | None]:
        if any(field.endswith(f'__{op}') for op in ALLOWED_OPERATORS):
            field_name, operator = field.rsplit('__', 1)
            return field_name, operator
        return field, None

    def create_filter_kwargs(self, attrs: dict) -> dict:
        filter_kwargs = {}
        for field in self.fields:
            field_name, operator = self.get_field_operator(field)
            value = attrs.get(field_name)
            if value is None and getattr(self, 'serializer', None) is not None:
                instance = getattr(self.serializer, 'instance', None)
                if instance is not None:
                    value = getattr(instance, field_name, None)
            if value is None:
                continue
            filter_key = f'{field_name}__{operator}' if operator else field_name
            filter_kwargs[filter_key] = value
        return filter_kwargs

    def set_context(self, serializer: BaseSerializer) -> None:
        self.serializer = serializer

    def __call__(self, attrs: dict) -> None:
        filter_kwargs = self.create_filter_kwargs(attrs)
        if not filter_kwargs:
            return
        qs = self.queryset
        if self.condition is not None:
            qs = qs.filter(self.condition)
        instance = None
        if getattr(self, 'serializer', None) is not None:
            instance = getattr(self.serializer, 'instance', None)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.filter(**filter_kwargs).exists():
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
