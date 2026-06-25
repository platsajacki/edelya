from __future__ import annotations

from typing import TypedDict


class IngredientPayloadData(TypedDict):
    ingredient: str | None
    name: str
    category: str
    base_unit: str
    amount: float
    is_optional: bool
    new: bool
    suggested_ids: list[str]


class DishPayloadData(TypedDict):
    name: str
    recipe: str
    category: str
    ingredients: list[IngredientPayloadData]
