from collections.abc import Hashable


class SafeFormatDict(dict):
    def __missing__(self, key: Hashable) -> str:
        return f'{{{key}}}'
