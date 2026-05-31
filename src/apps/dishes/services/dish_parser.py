import json
from dataclasses import dataclass
from typing import Any

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.shared_params.response_format_json_schema import ResponseFormatJSONSchema

from apps.dishes.services.recipe_schema_builder import RecipeSchemaBuilder
from apps.settings.constants import GPT_MODEL
from apps.settings.model_enums import PromptName
from apps.settings.models import Prompt
from core.base.services import BaseService
from core.open_ai import openai_client


@dataclass
class RecipeAIResult:
    data: dict[str, Any]
    usage: dict[str, Any] | None


@dataclass
class RecipeAI(BaseService[RecipeAIResult]):
    source_text: str

    def request_ai(self, prompt: str) -> ChatCompletion:
        messages: list[ChatCompletionMessageParam] = [
            {'role': 'developer', 'content': prompt},
            {'role': 'user', 'content': self.source_text},
        ]
        response_format: ResponseFormatJSONSchema = {
            'type': 'json_schema',
            'json_schema': RecipeSchemaBuilder()(),
        }
        return openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            response_format=response_format,
        )

    def get_prompt(self) -> str:
        prompt = Prompt.objects.get_by_name(PromptName.TEXT_TO_DISH)
        return prompt.render_text()

    def act(self) -> RecipeAIResult:
        prompt = self.get_prompt()
        response = self.request_ai(prompt)
        raw_content = response.choices[0].message.content or '{}'
        usage = response.usage.model_dump(mode='json') if response.usage is not None else None
        return RecipeAIResult(data=json.loads(raw_content), usage=usage)
