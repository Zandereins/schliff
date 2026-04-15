"""Verify that importing scoring does NOT import litellm.

Security requirement T7: The core scoring engine must remain zero-dependency.
Importing litellm transitively would break 'pip install schliff' (no extras).
"""
import sys


def test_scoring_import_does_not_import_litellm():
    """Importing the scoring package must NOT trigger a litellm import."""
    # Remove litellm from sys.modules if present (clean state)
    for mod_name in list(sys.modules):
        if mod_name.startswith("litellm"):
            del sys.modules[mod_name]

    # Import scoring — this is what 'schliff score' does
    import scoring  # noqa: F401

    # Verify litellm was not pulled in
    litellm_modules = [m for m in sys.modules if m.startswith("litellm")]
    assert litellm_modules == [], (
        f"Importing 'scoring' transitively imported litellm modules: {litellm_modules}. "
        f"This breaks 'pip install schliff' (without [evolve] extra)."
    )

def test_evolve_package_import_does_not_import_litellm():
    """Importing evolve package must NOT trigger a litellm import."""
    for mod_name in list(sys.modules):
        if mod_name.startswith("litellm"):
            del sys.modules[mod_name]

    import evolve  # noqa: F401

    litellm_modules = [m for m in sys.modules if m.startswith("litellm")]
    assert litellm_modules == [], (
        f"Importing 'evolve' transitively imported litellm modules: {litellm_modules}."
    )

def test_evolve_content_import_safe():
    """evolve.content must not import litellm."""
    for mod_name in list(sys.modules):
        if mod_name.startswith("litellm"):
            del sys.modules[mod_name]

    from evolve import content  # noqa: F401

    litellm_modules = [m for m in sys.modules if m.startswith("litellm")]
    assert litellm_modules == []

def test_evolve_guard_import_safe():
    """evolve.guard must not import litellm."""
    for mod_name in list(sys.modules):
        if mod_name.startswith("litellm"):
            del sys.modules[mod_name]

    from evolve import guard  # noqa: F401

    litellm_modules = [m for m in sys.modules if m.startswith("litellm")]
    assert litellm_modules == []
