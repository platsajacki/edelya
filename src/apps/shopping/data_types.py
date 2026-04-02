from decimal import Decimal
from typing import TypedDict
from uuid import UUID


class IngredientTotalAmountData(TypedDict):
    ingredient_id: UUID
    ingredient__base_unit: str
    total_amount: Decimal
