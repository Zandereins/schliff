"""Scoring patterns — split into format-specific submodules.

This __init__.py re-exports all names from base.py and skill_md.py
for backward compatibility. Existing code using:
    from scoring.patterns import _RE_FRONTMATTER_NAME
continues to work unchanged.
"""
from scoring.patterns.base import *  # noqa: F401,F403
from scoring.patterns.base import __all__ as _base_all
from scoring.patterns.skill_md import *  # noqa: F401,F403
from scoring.patterns.skill_md import __all__ as _skill_md_all

# Phase 1b: system prompt patterns (added when module exists)
try:
    from scoring.patterns.system_prompt import *  # noqa: F401,F403
    from scoring.patterns.system_prompt import __all__ as _system_prompt_all
except ImportError:
    _system_prompt_all = []

# Update combined __all__
__all__ = list(_base_all) + list(_skill_md_all) + list(_system_prompt_all)
