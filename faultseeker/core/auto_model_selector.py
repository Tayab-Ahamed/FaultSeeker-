"""
Auto Model Selector — FaultSeeker++
=====================================
Detects which API keys / local models are available and returns
the best model to use, without requiring the user to specify one.

Priority order:
  1. Local Ollama (free, zero latency, no key needed)
  2. Qwen-turbo   (cheapest cloud alternative)
  3. Gemini-flash (Google free tier available)
  4. Grok-mini    (xAI)
  5. GPT-4o-mini  (OpenAI)
"""

import os
import subprocess
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Preference order for cloud fallback ────────────────────────────────
# Format: (env_var, model_name, label)
CLOUD_PREFERENCE = [
    ('DASHSCOPE_API_KEY', 'qwen-turbo',       'Qwen-Turbo (Alibaba)'),
    ('GOOGLE_API_KEY',    'gemini-2.0-flash', 'Gemini-2.0-Flash (Google)'),
    ('XAI_API_KEY',       'grok-3-mini',      'Grok-3-Mini (xAI)'),
    ('OPENAI_API_KEY',    'gpt-4o-mini',      'GPT-4o-Mini (OpenAI)'),
    ('ANTHROPIC_API_KEY', 'claude-3-haiku-20240307', 'Claude-3-Haiku (Anthropic)'),
]

# ── Local Ollama model preference order ────────────────────────────────
LOCAL_PREFERENCE = [
    'phi3:mini',
    'qwen2:0.5b',
    'tinyllama',
    'llama3:8b',
    'deepseek-r1:14b',
    'mistral',
]


def _get_ollama_models() -> list:
    """Return list of locally installed Ollama models."""
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:   # skip header
            parts = line.split()
            if parts:
                models.append(parts[0].lower())
        return models
    except Exception:
        return []


def _has_cloud_key(env_var: str) -> bool:
    """Return True if the env var is set and non-empty."""
    val = os.getenv(env_var, '').strip()
    return bool(val) and val not in ('sk-...', 'xai-...', 'AIza...', 'sk-ant-...')


def detect_best_local_model() -> str | None:
    """Return the best available local Ollama model, or None if Ollama isn't running."""
    installed = _get_ollama_models()
    if not installed:
        return None
    for preferred in LOCAL_PREFERENCE:
        for installed_model in installed:
            if preferred.lower() in installed_model:
                return preferred
    # Return whatever is installed first
    return installed[0] if installed else None


def detect_best_cloud_model() -> tuple[str, str] | tuple[None, None]:
    """
    Return (model_name, label) of the first cloud provider with an API key set.
    Returns (None, None) if no cloud keys are configured.
    """
    for env_var, model, label in CLOUD_PREFERENCE:
        if _has_cloud_key(env_var):
            return model, label
    return None, None


def auto_select_models(prefer_local: bool = True) -> dict:
    """
    Auto-detect and return the best available models for the pipeline.

    Returns:
        dict with keys:
          - 'cloud_model'  : str  (used for complex reasoning tasks)
          - 'local_model'  : str | None
          - 'use_hybrid'   : bool (True if both local + cloud available)
          - 'cloud_label'  : str  (human-readable provider name)
    """
    local_model = detect_best_local_model()
    cloud_model, cloud_label = detect_best_cloud_model()

    if cloud_model is None and local_model is None:
        raise RuntimeError(
            "\n❌ No LLM available!\n"
            "   Either:\n"
            "   • Start Ollama and pull a model: ollama pull phi3:mini\n"
            "   • Or set at least one API key in .env (see .env.example)"
        )

    use_hybrid = (local_model is not None) and (cloud_model is not None)

    # If only local is available, use it for everything
    effective_cloud = cloud_model or local_model

    result = {
        'cloud_model':  effective_cloud,
        'local_model':  local_model,
        'use_hybrid':   use_hybrid,
        'cloud_label':  cloud_label or 'Local (Ollama)',
    }

    logger.info(f"Auto-selected: cloud={effective_cloud}, local={local_model}, "
                f"hybrid={use_hybrid}")
    return result


def print_model_selection(config: dict):
    """Print a user-friendly summary of the selected models."""
    print("\n🤖 Auto-detected LLM Configuration:")
    print(f"   Cloud model  : {config['cloud_model']} ({config['cloud_label']})")
    if config['local_model']:
        print(f"   Local model  : {config['local_model']} (Ollama)")
    if config['use_hybrid']:
        print("   Mode         : Hybrid (local for simple, cloud for complex)")
    else:
        print("   Mode         : Single model (no hybrid routing)")
    print()
