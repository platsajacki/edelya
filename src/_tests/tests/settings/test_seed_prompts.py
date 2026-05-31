from pytest_mock import MockerFixture

from pathlib import Path

from apps.settings.model_enums import PromptName
from apps.settings.models import Prompt
from apps.settings.tasks.seed_prompts import SeedPromptsService, seed_prompts


class TestSeedPromptsService:
    def test_creates_missing_prompt(self, mocker: MockerFixture, tmp_path: Path) -> None:
        yaml_path = tmp_path / 'prompts.yaml'
        yaml_path.write_text(
            "prompts:\n  - name: text_to_dish\n    required_variables:\n      - VARIABLE\n    text: '{{VARIABLE}}'\n",
            encoding='utf-8',
        )
        mocker.patch('apps.settings.tasks.seed_prompts.PROMPTS_YAML_PATH', yaml_path)
        assert SeedPromptsService()() == 1
        prompt = Prompt.objects.get(name=PromptName.TEXT_TO_DISH)
        assert prompt.text == '{{VARIABLE}}'
        assert prompt.required_variables == ['VARIABLE']

    def test_does_not_update_existing_prompt(self, mocker: MockerFixture, tmp_path: Path) -> None:
        Prompt.objects.create(name=PromptName.TEXT_TO_DISH, text='Existing prompt')
        yaml_path = tmp_path / 'prompts.yaml'
        yaml_path.write_text('prompts:\n  - name: text_to_dish\n    text: Updated prompt\n', encoding='utf-8')
        mocker.patch('apps.settings.tasks.seed_prompts.PROMPTS_YAML_PATH', yaml_path)
        assert SeedPromptsService()() == 0
        assert Prompt.objects.get(name=PromptName.TEXT_TO_DISH).text == 'Existing prompt'


class TestSeedPromptsTask:
    def test_calls_service(self, mocker: MockerFixture) -> None:
        mock_call = mocker.patch.object(SeedPromptsService, '__call__', return_value=0)
        result = seed_prompts()
        mock_call.assert_called_once()
        assert 'Created 0 prompt(s).' in result
