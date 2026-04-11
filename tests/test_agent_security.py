"""
tests/test_agent_security.py

Tests for:
  - eval() removal: _extract_json raises ValueError on unparseable input (Fix 1)
  - JSON retry logic: _query_with_json_retry retries and returns {} on exhaustion (Fix 1)
  - Claude routing guard: build_provider_agent raises NotImplementedError (Fix 2)
  - API key validation: FaultSeekerConfig.__post_init__ raises RuntimeError (Fix 3)
  - urlparse chain detection: ContractInfoCollector correctly maps explorer URLs (Fix 4)
"""

import os
import sys
import types
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub antlr4 so solidityParser (transitively imported via data_collection)
# doesn't crash in test environments that don't have antlr4 installed.
# ---------------------------------------------------------------------------
if "antlr4" not in sys.modules:
    _antlr4 = types.ModuleType("antlr4")
    for _sub in [
        "antlr4.CommonTokenStream",
        "antlr4.InputStream",
        "antlr4.error.ErrorListener",
        "antlr4.error",
        "antlr4.tree",
        "antlr4.tree.Tree",
    ]:
        sys.modules[_sub] = types.ModuleType(_sub)
    # CommonTokenStream and InputStream need to be callable attrs on antlr4
    _antlr4.CommonTokenStream = MagicMock
    _antlr4.InputStream = MagicMock
    sys.modules["antlr4"] = _antlr4


# ── Fix 1a: eval() removed — _extract_json raises ValueError ─────────────────

class TestExtractJsonNoEval:

    def setup_method(self):
        from faultseeker.utils.agent import AbstractAgent

        class ConcreteAgent(AbstractAgent):
            def _send_message(self, user_message, temperature=0):
                return ""

        self.agent = ConcreteAgent.__new__(ConcreteAgent)
        self.agent.memory = []
        self.agent.model = "test-model"

    def test_valid_json_object_parses(self):
        result = self.agent._extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_valid_json_array_parses(self):
        result = self.agent._extract_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_in_markdown_fence_parses(self):
        text = '```json\n{"a": 1}\n```'
        result = self.agent._extract_json(text)
        assert result == {"a": 1}

    def test_json_in_generic_fence_parses(self):
        text = '```\n{"b": 2}\n```'
        result = self.agent._extract_json(text)
        assert result == {"b": 2}

    def test_embedded_json_object_extracted(self):
        text = 'Here is the result: {"vuln": true} end.'
        result = self.agent._extract_json(text)
        assert result == {"vuln": True}

    def test_pure_garbage_raises_value_error_not_eval(self):
        """Completely unparseable text must raise ValueError, never call eval()."""
        with patch("builtins.eval", side_effect=AssertionError("eval() must not be called")) as mock_eval:
            with pytest.raises(ValueError, match="Invalid JSON from LLM"):
                self.agent._extract_json("this is not json at all ~~~")
            mock_eval.assert_not_called()

    def test_python_dict_syntax_raises_value_error(self):
        """Python dict syntax (single quotes) is NOT valid JSON — must raise, not eval."""
        with pytest.raises(ValueError):
            self.agent._extract_json("{'key': 'value'}")

    def test_exec_injection_raises_value_error(self):
        """Malicious exec() payload in LLM response must never be executed."""
        payload = "__import__('os').system('echo pwned')"
        with pytest.raises(ValueError):
            self.agent._extract_json(payload)


# ── Fix 1b: JSON retry loop ───────────────────────────────────────────────────

class TestQueryWithJsonRetry:

    def _make_agent(self, responses):
        """Build a ConcreteAgent whose _send_message returns items from `responses`."""
        from faultseeker.utils.agent import AbstractAgent

        class ConcreteAgent(AbstractAgent):
            def __init__(self):
                self.memory = [{"role": "system", "content": "test"}]
                self.model = "test-model"
                self._responses = iter(responses)

            def _send_message(self, msg, temperature=0):
                self.memory.append({"role": "user", "content": msg})
                r = next(self._responses)
                self.memory.append({"role": "assistant", "content": r})
                return r

        return ConcreteAgent()

    def test_succeeds_on_first_try(self):
        agent = self._make_agent(['{"result": 1}'])
        result = agent._query_with_json_retry("prompt", temperature=0, max_retries=3)
        assert result == {"result": 1}

    def test_retries_on_bad_json_then_succeeds(self):
        agent = self._make_agent(["not json", '{"result": 2}'])
        result = agent._query_with_json_retry("prompt", temperature=0, max_retries=3)
        assert result == {"result": 2}

    def test_returns_empty_dict_after_all_retries_exhausted(self):
        agent = self._make_agent(["bad"] * 10)  # always bad
        result = agent._query_with_json_retry("prompt", temperature=0, max_retries=3)
        assert result == {}

    def test_retry_count_is_bounded(self):
        """Should call _send_message at most max_retries+1 times (1 initial + N retries)."""
        calls = []

        from faultseeker.utils.agent import AbstractAgent

        class TrackingAgent(AbstractAgent):
            def __init__(self):
                self.memory = [{"role": "system", "content": "test"}]
                self.model = "test-model"

            def _send_message(self, msg, temperature=0):
                calls.append(msg)
                self.memory.append({"role": "user", "content": msg})
                self.memory.append({"role": "assistant", "content": "bad"})
                return "bad"

        agent = TrackingAgent()
        agent._query_with_json_retry("initial", temperature=0, max_retries=2)
        # 1 initial + 2 retries = 3 total calls
        assert len(calls) == 3


# ── Fix 2: Claude routing guard ───────────────────────────────────────────────

class TestClaudeRoutingGuard:

    def test_claude_model_raises_not_implemented(self):
        """build_provider_agent must reject claude-* with NotImplementedError."""
        from faultseeker.utils.agent import build_provider_agent
        with pytest.raises(NotImplementedError, match="Claude model"):
            build_provider_agent("system prompt", "claude-3-haiku-20240307")

    def test_claude_sonnet_raises_not_implemented(self):
        from faultseeker.utils.agent import build_provider_agent
        with pytest.raises(NotImplementedError):
            build_provider_agent("system prompt", "claude-3-5-sonnet-20241022")

    def test_non_claude_cloud_model_does_not_raise(self):
        """gemini-* should NOT raise NotImplementedError — only Claude is blocked."""
        from faultseeker.utils.agent import build_provider_agent
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-key"}):
            # Should not raise NotImplementedError (may raise ValueError for bad key, that's fine)
            try:
                build_provider_agent("system prompt", "gemini-1.5-flash")
            except NotImplementedError:
                pytest.fail("gemini model should not raise NotImplementedError")
            except Exception:
                pass  # Other errors (auth etc.) are expected in test env

    def test_local_ollama_model_does_not_raise(self):
        """Local model names must route to OllmaAgent without hitting the Claude guard."""
        from faultseeker.utils.agent import build_provider_agent, OllmaAgent
        agent = build_provider_agent("system prompt", "llama3:8b")
        assert isinstance(agent, OllmaAgent)


# ── Fix 3: API key validation ─────────────────────────────────────────────────

class TestApiKeyValidation:

    def test_missing_openai_key_raises_runtime_error(self):
        """Instantiating config with a gpt model and no OPENAI_API_KEY must fail fast."""
        from faultseeker.core.config import FaultSeekerConfig
        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                                  "XAI_API_KEY", "DASHSCOPE_API_KEY", "GOOGLE_API_KEY")}
        # load_dotenv is imported locally inside validate_api_keys(); patch it at source.
        with patch("dotenv.load_dotenv", return_value=None), \
             patch.dict(os.environ, clean_env, clear=True):
            with pytest.raises(RuntimeError, match="Missing API key"):
                FaultSeekerConfig(forensics_model="gpt-4o-mini",
                                  function_analysis_model="gpt-4o-mini")

    def test_present_openai_key_does_not_raise(self):
        """A valid OPENAI_API_KEY must allow config instantiation without error."""
        from faultseeker.core.config import FaultSeekerConfig
        with patch("dotenv.load_dotenv", return_value=None), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-1234"}):
            config = FaultSeekerConfig(forensics_model="gpt-4o-mini",
                                       function_analysis_model="gpt-4o-mini")
            assert config.forensics_model == "gpt-4o-mini"

    def test_local_model_config_never_needs_api_key(self):
        """An all-local (Ollama) config must not require any cloud API key."""
        from faultseeker.core.config import FaultSeekerConfig
        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                                  "XAI_API_KEY", "DASHSCOPE_API_KEY", "GOOGLE_API_KEY")}
        with patch("dotenv.load_dotenv", return_value=None), \
             patch.dict(os.environ, clean_env, clear=True):
            config = FaultSeekerConfig(forensics_model="llama3:8b",
                                       function_analysis_model="llama3:8b")
            assert config.forensics_model == "llama3:8b"

    def test_validate_api_keys_is_callable_directly(self):
        """validate_api_keys() must be a callable method on FaultSeekerConfig."""
        from faultseeker.core.config import FaultSeekerConfig
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            config = FaultSeekerConfig.__new__(FaultSeekerConfig)
            config.forensics_model = "gpt-4o-mini"
            config.function_analysis_model = "gpt-4o-mini"
            config.cloud_model = ""
            config.auto_route = False
            config.local_model = "llama3:8b"
            config.validate_api_keys()  # must not raise


# ── Fix 4: urlparse-based chain detection ─────────────────────────────────────

def _load_collector_class():
    """
    Load ContractInfoCollector directly from its file, bypassing
    data_collection/__init__.py which triggers solidityParser → antlr4.
    """
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "contract_info_collector_isolated",
        pathlib.Path(__file__).parent.parent
        / "faultseeker" / "data_collection" / "contract_info_collector.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ContractInfoCollector


class TestUrlparseChainDetection:

    def setup_method(self):
        CollectorClass = _load_collector_class()
        self.collector = CollectorClass.__new__(CollectorClass)
        self.collector.contract_link = None

    def _detect(self, txn_link, address="0xDEAD"):
        self.collector.txn_link = txn_link
        self.collector._get_contract_address_link(address, "")
        return self.collector.contract_link

    def test_etherscan_io_maps_to_mainnet(self):
        link = self._detect("https://etherscan.io/tx/0x" + "a" * 64)
        assert "etherscan.io" in link

    def test_optimistic_etherscan_not_misclassified_as_eth(self):
        """The old code sent optimism txns to etherscan.io."""
        link = self._detect("https://optimistic.etherscan.io/tx/0x" + "a" * 64)
        assert "optimistic.etherscan.io" in link
        assert link.startswith("https://optimistic.etherscan.io")

    def test_bscscan_maps_correctly(self):
        link = self._detect("https://bscscan.com/tx/0x" + "a" * 64)
        assert "bscscan.com" in link

    def test_polygonscan_maps_correctly(self):
        link = self._detect("https://polygonscan.com/tx/0x" + "a" * 64)
        assert "polygonscan.com" in link

    def test_basescan_maps_correctly(self):
        link = self._detect("https://basescan.org/tx/0x" + "a" * 64)
        assert "basescan.org" in link

    def test_unknown_domain_falls_back_to_etherscan(self):
        link = self._detect("https://unknown-explorer.example.com/tx/0x" + "a" * 64)
        assert "etherscan.io" in link
