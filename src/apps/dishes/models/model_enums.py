from django.db import models


class Unit(models.TextChoices):
    MILLIGRAM = 'milligram', 'Миллиграмм'
    GRAM = 'gram', 'Грамм'
    KILOGRAM = 'kilogram', 'Килограмм'

    MILLILITER = 'milliliter', 'Миллилитр'
    LITER = 'liter', 'Литр'

    PIECE = 'piece', 'Штука'
    SLICE = 'slice', 'Ломтик'

    TEASPOON = 'teaspoon', 'Чайная ложка'
    TABLESPOON = 'tablespoon', 'Столовая ложка'

    GLASS = 'glass', 'Стакан'
    CUP = 'cup', 'Чашка'

    BUNCH = 'bunch', 'Пучок'
    CAN = 'can', 'Банка'

    PINCH = 'pinch', 'Щепотка'

    CLOVE = 'clove', 'Зубчик'
    TO_TASTE = 'to_taste', 'По вкусу'
