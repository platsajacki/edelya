from decimal import Decimal
from typing import TypedDict
from uuid import UUID


class IngredientTotalAmountData(TypedDict):
    ingredient_id: UUID
    total_amount: Decimal
