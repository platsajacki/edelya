from collections.abc import Callable

from drf_spectacular.utils import extend_schema_view


def extend_schema_view_from_class(schema_cls: type) -> Callable:
    """Return an extend_schema_view wrapper that maps common view action names
    from a schema class to drf-spectacular's extend_schema_view.

    Usage:
        @extend_schema_view_from_class(MyViewSetSchema)
        class MyViewSet(...):
            ...

    The helper will look for attributes on `schema_cls`
    and pass any found to the underlying `extend_schema_view`.
    """
    action_names = {
        'list',
        'retrieve',
        'create',
        'update',
        'partial_update',
        'destroy',
        'get',
        'post',
        'put',
        'patch',
        'delete',
    }
    if hasattr(schema_cls, 'custom_actions'):
        action_names.update(schema_cls.custom_actions)
    mapping = {name: getattr(schema_cls, name) for name in action_names if hasattr(schema_cls, name)}
    return extend_schema_view(**mapping)
