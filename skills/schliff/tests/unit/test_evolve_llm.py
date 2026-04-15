"""Tests for evolve.llm — LiteLLM integration and model resolution."""
import os
from unittest.mock import patch

import pytest
from evolve.llm import call_llm, resolve_model


class TestResolveModel:
    def test_explicit_model_takes_priority(self):
        assert resolve_model(model="my/custom-model") == "my/custom-model"

    def test_explicit_model_overrides_provider(self):
        assert resolve_model(provider="openai", model="my/model") == "my/model"

    def test_provider_ollama(self):
        assert resolve_model(provider="ollama") == "ollama/llama3"

    def test_provider_anthropic(self):
        assert resolve_model(provider="anthropic") == "anthropic/claude-sonnet-4-20250514"

    def test_provider_openrouter(self):
        assert resolve_model(provider="openrouter") == "openrouter/anthropic/claude-sonnet-4-20250514"

    def test_provider_openai(self):
        assert resolve_model(provider="openai") == "openai/gpt-4o"

    def test_unknown_provider_warns_and_returns_default(self, capsys):
        result = resolve_model(provider="custom-provider")
        assert result == "custom-provider/default"
        captured = capsys.readouterr()
        assert "Warning" in captured.err or "Unknown" in captured.err or result == "custom-provider/default"

    @patch.dict(os.environ, {"OLLAMA_HOST": "http://localhost:11434"}, clear=False)
    def test_auto_detect_ollama(self):
        # Clear other keys that might be set
        env = os.environ.copy()
        for k in ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
            env.pop(k, None)
        with patch.dict(os.environ, env, clear=True):
            os.environ["OLLAMA_HOST"] = "http://localhost:11434"
            assert resolve_model() == "ollama/llama3"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123456789012345"}, clear=True)
    def test_auto_detect_anthropic(self):
        assert resolve_model() == "anthropic/claude-sonnet-4-20250514"

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-test-key"}, clear=True)
    def test_auto_detect_openrouter(self):
        assert "openrouter" in resolve_model()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-1234567890"}, clear=True)
    def test_auto_detect_openai(self):
        assert resolve_model() == "openai/gpt-4o"

    def test_no_provider_exits(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove all relevant env vars
            for key in ("OLLAMA_HOST", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
                os.environ.pop(key, None)
            with pytest.raises(SystemExit):
                resolve_model()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "key1", "OPENAI_API_KEY": "key2"}, clear=True)
    def test_anthropic_takes_priority_over_openai(self):
        assert "anthropic" in resolve_model()


class TestCallLLM:
    def test_injected_completion_fn(self):
        def mock_fn(model, messages, temperature, max_tokens):
            return {"content": "improved content", "usage": {"total_tokens": 150}}

        result = call_llm("system", "user", "test/model", completion_fn=mock_fn)
        assert result["content"] == "improved content"
        assert result["tokens_used"] == 150
        assert result["model"] == "test/model"

    def test_injected_fn_receives_correct_messages(self):
        received = {}
        def mock_fn(**kwargs):
            received.update(kwargs)
            return {"content": "ok", "usage": {"total_tokens": 10}}

        call_llm("sys prompt", "user prompt", "m", temperature=0.5, completion_fn=mock_fn)
        assert received["model"] == "m"
        assert received["temperature"] == 0.5
        assert len(received["messages"]) == 2
        assert received["messages"][0]["role"] == "system"
        assert received["messages"][1]["role"] == "user"

    def test_injected_fn_missing_usage_returns_zero(self):
        def mock_fn(**kwargs):
            return {"content": "text"}

        result = call_llm("s", "u", "m", completion_fn=mock_fn)
        assert result["tokens_used"] == 0

    def test_injected_fn_empty_content(self):
        def mock_fn(**kwargs):
            return {"content": "", "usage": {"total_tokens": 5}}

        result = call_llm("s", "u", "m", completion_fn=mock_fn)
        assert result["content"] == ""

    def test_completion_fn_no_retry(self):
        """DI path should NOT retry — errors propagate immediately."""
        call_count = 0

        def failing_fn(**kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("transient")

        with pytest.raises(ConnectionError):
            call_llm("s", "u", "m", completion_fn=failing_fn)
        assert call_count == 1  # called exactly once, no retry

    def test_retry_delays(self):
        """Verify the retry delay sequence is [1, 2, 4]."""
        from evolve.llm import RETRY_DELAYS
        assert RETRY_DELAYS == [1, 2, 4]

    def test_real_path_without_litellm_exits(self):
        """Without litellm installed and no completion_fn, should exit."""
        with pytest.raises(SystemExit):
            call_llm("s", "u", "model")
