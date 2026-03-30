"""LiteLLM integration for the evolution engine.

LiteLLM is lazy-imported — this module can be imported without litellm installed.
Install via: pip install schliff[evolve]
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable, Optional

from evolve.sanitize import redact_exception

# Type alias for the completion function (dependency injection)
CompletionFn = Callable[..., Any]


def _check_litellm_available() -> None:
    """Check if litellm is installed, raise clear error if not."""
    try:
        import litellm  # noqa: F401
    except ImportError:
        print(
            "Error: LLM evolution requires litellm.\n"
            "Install with: pip install schliff[evolve]\n"
            "Or use --budget 0 for deterministic-only mode.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def resolve_model(provider: Optional[str] = None, model: Optional[str] = None) -> str:
    """Resolve which model to use via fallback chain.

    Priority:
    1. Explicit --model flag
    2. Explicit --provider → default model for that provider
    3. OLLAMA_HOST env → ollama/llama3 (free, local)
    4. ANTHROPIC_API_KEY → anthropic/claude-sonnet-4-20250514
    5. OPENROUTER_API_KEY → openrouter/anthropic/claude-sonnet-4-20250514
    6. OPENAI_API_KEY → openai/gpt-4o
    """
    if model:
        return model

    if provider:
        defaults = {
            "ollama": "ollama/llama3",
            "anthropic": "anthropic/claude-sonnet-4-20250514",
            "openrouter": "openrouter/anthropic/claude-sonnet-4-20250514",
            "openai": "openai/gpt-4o",
        }
        if provider in defaults:
            return defaults[provider]
        # Unknown provider — warn but allow (user may have custom LiteLLM setup)
        print(
            f"Warning: Unknown provider '{provider}'. "
            f"Known providers: {', '.join(sorted(defaults))}. "
            f"Using '{provider}/default' — ensure LiteLLM supports this.",
            file=sys.stderr,
        )
        return f"{provider}/default"

    # Auto-detect from environment
    if os.environ.get("OLLAMA_HOST"):
        return "ollama/llama3"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic/claude-sonnet-4-20250514"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter/anthropic/claude-sonnet-4-20250514"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai/gpt-4o"

    print(
        "Error: No LLM provider configured.\n"
        "Set one of: OLLAMA_HOST, ANTHROPIC_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY\n"
        "Or use --budget 0 for deterministic-only mode (free, no LLM).",
        file=sys.stderr,
    )
    raise SystemExit(1)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    completion_fn: Optional[CompletionFn] = None,
) -> dict:
    """Call an LLM via LiteLLM or injected completion function.

    Args:
        completion_fn: Optional callable for testing. If provided, litellm is NOT imported.
                       Must accept (model, messages, temperature, max_tokens) kwargs
                       and return a dict with "content" and "usage" keys.

    Returns:
        {"content": str, "tokens_used": int, "model": str}

    Raises:
        SystemExit on unrecoverable errors (with redacted messages).
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if completion_fn is not None:
        # Dependency injection path — for testing
        result = completion_fn(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens,
        )
        return {
            "content": result.get("content", ""),
            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
            "model": model,
        }

    # Real LiteLLM path
    _check_litellm_available()
    try:
        import litellm
        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        tokens = (usage.prompt_tokens or 0) + (usage.completion_tokens or 0) if usage else 0
        return {
            "content": content,
            "tokens_used": tokens,
            "model": model,
        }
    except KeyboardInterrupt:
        raise
    except SystemExit:
        raise
    except Exception as exc:
        # SECURITY: Never expose raw tracebacks — they may contain API keys in locals
        safe_msg = redact_exception(exc)
        print(f"Error: LLM call failed: {safe_msg}", file=sys.stderr)
        print("Hint: Use --budget 0 to skip LLM and run deterministic patches only.", file=sys.stderr)
        raise SystemExit(1)
