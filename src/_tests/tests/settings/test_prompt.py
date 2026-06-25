import pytest

from django.core.exceptions import ValidationError

from apps.settings.model_enums import PromptName
from apps.settings.models import Prompt


class TestPrompt:
    def test_saves_prompt_with_required_variables(self) -> None:
        prompt = Prompt.objects.create(
            name=PromptName.TEXT_TO_DISH,
            text='{{VARIABLE}}',
            required_variables=['VARIABLE'],
        )
        assert prompt.required_variables == ['VARIABLE']

    def test_does_not_save_prompt_without_required_variable(self) -> None:
        with pytest.raises(ValidationError):
            Prompt.objects.create(
                name=PromptName.TEXT_TO_DISH,
                text='Prompt',
                required_variables=['VARIABLE'],
            )
