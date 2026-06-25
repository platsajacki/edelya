from django.db import models


class PromptName(models.TextChoices):
    TEXT_TO_DISH = 'text_to_dish', 'Текст в блюдо'
