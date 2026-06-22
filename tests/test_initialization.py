import importlib
import os

import pytest

from forelius.initialization import (
    DEFAULT_REQUIRED_ENVIRONMENT,
    ForeliusConfigurationError,
    ensure_initialized,
    initialize,
)


def reset_initialization_module():
    import forelius.initialization as initialization

    return importlib.reload(initialization)


def test_importing_forelius_does_not_require_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import forelius

    assert forelius is not None


def test_initialize_succeeds_when_required_env_vars_are_present(monkeypatch) -> None:
    initialization = reset_initialization_module()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    assert initialization.initialize() is None


def test_initialize_raises_when_required_env_vars_are_missing(monkeypatch, tmp_path) -> None:
    initialization = reset_initialization_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(initialization.ForeliusConfigurationError, match="ANTHROPIC_API_KEY"):
        initialization.initialize()


def test_initialize_loads_dotenv_when_required_env_var_is_absent(monkeypatch, tmp_path) -> None:
    initialization = reset_initialization_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=dotenv-key\n")

    initialization.initialize()

    assert os.environ["ANTHROPIC_API_KEY"] == "dotenv-key"


def test_initialize_does_not_override_existing_env_var_with_dotenv(monkeypatch, tmp_path) -> None:
    initialization = reset_initialization_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "existing-key")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=dotenv-key\n")

    initialization.initialize()

    assert os.environ["ANTHROPIC_API_KEY"] == "existing-key"


def test_initialize_accepts_custom_required_environment(monkeypatch) -> None:
    initialization = reset_initialization_module()
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")

    assert initialization.initialize(["CUSTOM_API_KEY"]) is None


def test_ensure_initialized_initializes_from_default_environment(monkeypatch) -> None:
    initialization = reset_initialization_module()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    assert initialization.ensure_initialized() is None


def test_default_required_environment_uses_anthropic_key() -> None:
    assert DEFAULT_REQUIRED_ENVIRONMENT == ["ANTHROPIC_API_KEY"]
