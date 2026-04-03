import abc
import json
import re
from typing import Dict, List, Any, Union, Optional
import traceback
from ollama import chat
from openai import OpenAI
import os
from dotenv import load_dotenv


# ── Provider registry ──────────────────────────────────────────────────
# Maps model-name prefix → (base_url, env_var_for_api_key)
PROVIDER_CONFIG = {
    # OpenAI
    'gpt-':     ('https://api.openai.com/v1',                                    'OPENAI_API_KEY'),
    'o1-':      ('https://api.openai.com/v1',                                    'OPENAI_API_KEY'),
    'o3-':      ('https://api.openai.com/v1',                                    'OPENAI_API_KEY'),
    'o4-':      ('https://api.openai.com/v1',                                    'OPENAI_API_KEY'),
    # xAI Grok (OpenAI-compatible)
    'grok-':    ('https://api.x.ai/v1',                                          'XAI_API_KEY'),
    # Alibaba Qwen via DashScope (OpenAI-compatible)
    'qwen-':    ('https://dashscope.aliyuncs.com/compatible-mode/v1',            'DASHSCOPE_API_KEY'),
    # Google Gemini (OpenAI-compatible endpoint)
    'gemini-':  ('https://generativelanguage.googleapis.com/v1beta/openai/',     'GOOGLE_API_KEY'),
    # Anthropic Claude (NB: not OpenAI-compatible natively — requires anthropic sdk)
    'claude-':  ('https://api.anthropic.com/v1',                                 'ANTHROPIC_API_KEY'),
}

# Models that support native JSON response_format
JSON_MODE_MODELS = {
    'gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano',
    'gpt-4-turbo',
    'grok-3', 'grok-3-mini', 'grok-2',
    'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash',
    'qwen-plus', 'qwen-turbo', 'qwen-max',
}


JSON_RETRY_PROMPT = (
    "Your previous response was not valid JSON. "
    "Return ONLY a valid JSON object or array. "
    "No explanations, no markdown fences, no extra text."
)


class AbstractAgent(abc.ABC):

    def __init__(
        self,
        task: str,
        model_name: str,
    ):
        self.model = model_name
        self.memory = []
        self._init_resources(task)

    def _init_resources(self, task):
        system_message = {
            "role": "system",
            "content": '\n'.join([task])
        }
        self.memory.append(system_message)

    # to be implemented in the child class
    def _send_message(self, user_message: str, temperature=0) -> str:
        pass

    # ── Robust JSON parser (Fix 1) ─────────────────────────────────────
    def _extract_json(self, text: str):
        """
        Try to extract a JSON object/array from raw LLM text using
        multiple strategies in order of preference:
          1. json.loads on the stripped text
          2. Extract from ```json ... ``` fence
          3. Extract from ``` ... ``` fence
          4. Regex extraction of first {...} or [...]
          5. eval() fallback (last resort)
        """
        # Strategy 1 — clean and direct parse
        cleaned = text.strip().strip('`').strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # Strategy 2 — ```json fence
        fence_json = re.search(r'```json\s*([\s\S]*?)```', text)
        if fence_json:
            try:
                return json.loads(fence_json.group(1).strip())
            except Exception:
                pass

        # Strategy 3 — generic ``` fence
        fence_generic = re.search(r'```\s*([\s\S]*?)```', text)
        if fence_generic:
            try:
                return json.loads(fence_generic.group(1).strip())
            except Exception:
                pass

        # Strategy 4 — regex for first {...} or [...]
        obj_match = re.search(r'(\{[\s\S]*\})', text)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except Exception:
                pass

        arr_match = re.search(r'(\[[\s\S]*\])', text)
        if arr_match:
            try:
                return json.loads(arr_match.group(1))
            except Exception:
                pass

        # Strategy 5 — eval last resort
        try:
            return eval(cleaned)
        except Exception:
            pass

        return text  # give back raw string if all fail

    def _process_json_response(self, response: str) -> Dict[str, Any]:
        return self._extract_json(response)

    def _process_dict_response(self, response: str) -> Dict[str, Any]:
        result = self._extract_json(response)
        if isinstance(result, (dict, list)):
            return result
        return [response]

    def _process_response(self, response: str, format: str) -> Union[List[str], Dict[str, Any]]:
        if format == 'json':
            return self._process_json_response(response)
        elif format == 'dict':
            return self._process_dict_response(response)
        return response

    def _query_with_json_retry(self, user_message: str, temperature: float, max_retries: int = 3) -> Any:
        """
        Query the LLM and retry up to max_retries times if the output
        is not valid JSON. On each retry injecting a correction prompt.
        """
        result_raw = self._send_message(user_message, temperature)
        parsed = self._extract_json(result_raw)

        # If parsed is still a raw string (not dict/list), retry
        retries = 0
        while isinstance(parsed, str) and retries < max_retries:
            retries += 1
            result_raw = self._send_message(JSON_RETRY_PROMPT, temperature)
            parsed = self._extract_json(result_raw)

        return parsed

    def query(self, user_message: str, temperature=0, format='json') -> Any:
        if format == 'str':
            return self._send_message(user_message, temperature)

        # Use retry-enabled query for JSON formats
        try:
            return self._query_with_json_retry(user_message, temperature)
        except Exception:
            traceback.print_exc()
            raw = self._send_message(user_message, temperature)
            return self._process_response(raw, format)


class OllmaAgent(AbstractAgent):
    def __init__(self, task, model_name: str = "deepseek-r1:14b"):
        super().__init__(task, model_name)

    def _send_message(self, user_message: str, temperature=0.3) -> str:
        self.memory.append({"role": "user", "content": user_message})
        try:
            response = chat(
                model=self.model,
                messages=self.memory,
                options={'temperature': temperature}
            )
            assistant_response = response['message']['content']
            self.memory.append({"role": "assistant", "content": assistant_response})
            return assistant_response
        except Exception:
            traceback.print_exc()
            return "An error occurred."


class GPTAgent(AbstractAgent):
    """OpenAI GPT agent (gpt-4o, gpt-4.1, o1, o3 etc.)"""

    def __init__(self, task, model_name):
        load_dotenv()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        super().__init__(task, model_name=model_name)

    def _truncate_history(self, history, max_turns=1):
        system_prompt = history[0]
        message_pairs = history[1:]
        truncated = message_pairs[-(max_turns * 2):]
        return [system_prompt] + truncated

    def _send_message(self, user_message, temperature=0):
        client = OpenAI(api_key=self.openai_api_key)
        try:
            user_message = user_message[:10000]
            self.memory.append({"role": "user", "content": user_message})
            kwargs = dict(
                messages=self._truncate_history(self.memory),
                model=self.model,
                temperature=temperature,
            )
            if self.model in JSON_MODE_MODELS or any(
                self.model.startswith(p) for p in ('gpt-4o', 'gpt-4.1', 'gpt-4-turbo')
            ):
                kwargs['response_format'] = {"type": "json_object"}
            chat_completion = client.chat.completions.create(**kwargs)
            reply = chat_completion.choices[0].message.content
            self.memory.append({"role": "assistant", "content": reply})
            return reply
        except Exception:
            traceback.print_exc()
            self.memory.append({"role": "assistant", "content": ''})
            return "An error occurred."


class UniversalAgent(AbstractAgent):
    """
    Multi-provider agent supporting Qwen, Grok, Gemini, and any
    OpenAI-compatible REST API. Automatically selects the right
    base_url and API key from PROVIDER_CONFIG based on model prefix.
    """

    def __init__(self, task: str, model_name: str,
                 base_url: Optional[str] = None,
                 api_key: Optional[str] = None):
        load_dotenv()
        # Auto-detect provider from model prefix
        detected_base_url, env_var = self._detect_provider(model_name)
        self.base_url = base_url or detected_base_url
        self.api_key  = api_key  or os.getenv(env_var, '')
        if not self.api_key:
            raise ValueError(
                f"No API key found for model '{model_name}'. "
                f"Set the '{env_var}' environment variable in .env"
            )
        super().__init__(task, model_name=model_name)

    @staticmethod
    def _detect_provider(model_name: str):
        for prefix, config in PROVIDER_CONFIG.items():
            if model_name.startswith(prefix):
                return config  # (base_url, env_var)
        # Default to OpenAI
        return 'https://api.openai.com/v1', 'OPENAI_API_KEY'

    def _truncate_history(self, history, max_turns=2):
        system_prompt = history[0]
        message_pairs = history[1:]
        truncated = message_pairs[-(max_turns * 2):]
        return [system_prompt] + truncated

    def _send_message(self, user_message: str, temperature: float = 0) -> str:
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        try:
            user_message = user_message[:10000]
            self.memory.append({"role": "user", "content": user_message})
            kwargs = dict(
                messages=self._truncate_history(self.memory),
                model=self.model,
                temperature=temperature,
            )
            # Enable JSON mode if model supports it
            if self.model in JSON_MODE_MODELS:
                kwargs['response_format'] = {"type": "json_object"}
            chat_completion = client.chat.completions.create(**kwargs)
            reply = chat_completion.choices[0].message.content
            self.memory.append({"role": "assistant", "content": reply})
            return reply
        except Exception:
            traceback.print_exc()
            self.memory.append({"role": "assistant", "content": ''})
            return "An error occurred."


def build_provider_agent(task: str, model_name: str) -> AbstractAgent:
    """
    Factory — returns the right agent class for a given model name.

    Supported prefixes:
      gpt-*, o1-*, o3-*, o4-*  → GPTAgent (OpenAI)
      grok-*                   → UniversalAgent (xAI)
      qwen-*                   → UniversalAgent (Alibaba DashScope)
      gemini-*                 → UniversalAgent (Google)
      claude-*                 → UniversalAgent (Anthropic-compat)
      <anything else>          → OllmaAgent (local Ollama)
    """
    cloud_prefixes = tuple(PROVIDER_CONFIG.keys())
    if not any(model_name.startswith(p) for p in cloud_prefixes):
        return OllmaAgent(task, model_name)
    openai_prefixes = ('gpt-', 'o1-', 'o3-', 'o4-')
    if any(model_name.startswith(p) for p in openai_prefixes):
        return GPTAgent(task, model_name)
    return UniversalAgent(task, model_name)