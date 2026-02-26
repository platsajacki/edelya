from django.db import models


class Unit(models.TextChoices):
    MG = 'mg', 'Миллиграммы'
    G = 'g', 'Граммы'
    KG = 'kg', 'Килограммы'
    ML = 'ml', 'Миллилитры'
    L = 'l', 'Литры'
    PCS = 'pcs', 'Штуки'
    TSP = 'tsp', 'Чайные ложки'
    TBSP = 'tbsp', 'Столовые ложки'
