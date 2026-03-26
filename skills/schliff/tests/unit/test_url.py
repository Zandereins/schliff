"""Unit tests for fetch_url_safe() security validation.

These tests verify that validation logic rejects invalid inputs without
making any network calls.
"""
import pytest
import sys
import os

# Ensure scripts dir is on sys.path
_SCRIPTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "scripts"
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from shared import fetch_url_safe


def test_fetch_url_rejects_http():
    """fetch_url_safe must reject plain HTTP URLs."""
    with pytest.raises(ValueError, match="Only HTTPS"):
        fetch_url_safe("http://example.com/file.md")


def test_fetch_url_rejects_disallowed_host():
    """fetch_url_safe must reject hosts not in the allowlist."""
    with pytest.raises(ValueError, match="not in the allowed list"):
        fetch_url_safe("https://evil.com/file.md")
