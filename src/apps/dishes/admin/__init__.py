from apps.dishes.admin.ai_drafts import DishAIDraftAdmin
from apps.dishes.admin.dishes import DishAdmin, DishCategoryAdmin, DishIngredientInline
from apps.dishes.admin.ingredients import IngredientAdmin, IngredientCategoryAdmin

__all__ = [
    'DishAIDraftAdmin',
    'DishCategoryAdmin',
    'DishAdmin',
    'DishIngredientInline',
    'IngredientCategoryAdmin',
    'IngredientAdmin',
]
