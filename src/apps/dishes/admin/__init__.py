from apps.dishes.admin.dishes import DishAdmin, DishCategoryAdmin, DishIngredientInline
from apps.dishes.admin.ingredients import IngredientAdmin, IngredientCategoryAdmin

__all__ = [
    'DishCategoryAdmin',
    'DishAdmin',
    'DishIngredientInline',
    'IngredientCategoryAdmin',
    'IngredientAdmin',
]
