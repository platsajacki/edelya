import json
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, Literal, TypedDict

from django.conf import settings
from django.core.cache import caches

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.shared_params.response_format_json_schema import ResponseFormatJSONSchema

from apps.dishes.services.recipe_schema_builder import RecipeSchemaBuilder
from apps.settings.model_enums import PromptName
from apps.settings.models import Prompt
from core.base.services import BaseService
from core.open_ai import openai_client

ai_cache = caches[settings.AI_CACHE_ALIAS]


type RecipeParseErrorCode = Literal[
    'not_recipe',
    'too_short',
    'not_enough_data',
    'multiple_recipes',
    'prompt_injection',
    'not_processable',
]


class RecipeAIDishData(TypedDict):
    name: str
    recipe: str
    category_name: str


class RecipeAIIngredientData(TypedDict):
    name: str
    category_name: str
    base_unit: str
    amount: float
    position: int
    is_optional: bool


class RecipeAISuccessData(TypedDict):
    status: Literal['success']
    dish: RecipeAIDishData
    ingredients: list[RecipeAIIngredientData]


class RecipeAIErrorData(TypedDict):
    status: Literal['error']
    error_code: RecipeParseErrorCode
    error_message: str


type RecipeAIParsedData = RecipeAISuccessData | RecipeAIErrorData


class RecipeAIData(TypedDict):
    result: RecipeAIParsedData


@dataclass
class RecipeAIResult:
    data: RecipeAIData
    usage: dict[str, Any] | None


@dataclass
class RecipeAI(BaseService[RecipeAIResult]):
    source_text: str
    _cache_key_prefix: str = dc_field(default='ai:prompt:', init=False)
    _cache_timeout: int = dc_field(default=60 * 60 * 24, init=False)  # 24 часа

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
            model=settings.GPT_MODEL,
            messages=messages,
            response_format=response_format,
        )

    def get_cache_key(self, prompt_name: PromptName) -> str:
        return f'{self._cache_key_prefix}{prompt_name.value}'

    def _get_prompt(self) -> str:
        prompt = Prompt.objects.get_by_name(PromptName.TEXT_TO_DISH)
        return prompt.render_text()

    def get_prompt(self) -> str:
        cache_key = self.get_cache_key(PromptName.TEXT_TO_DISH)
        if cached_prompt := ai_cache.get(cache_key):
            return cached_prompt
        prompt = self._get_prompt()
        ai_cache.set(cache_key, prompt, timeout=self._cache_timeout)
        return prompt

    def act(self) -> RecipeAIResult:
        prompt = self.get_prompt()
        response = self.request_ai(prompt)
        raw_content = response.choices[0].message.content or '{}'
        usage = response.usage.model_dump(mode='json') if response.usage is not None else None
        return RecipeAIResult(data=json.loads(raw_content), usage=usage)
