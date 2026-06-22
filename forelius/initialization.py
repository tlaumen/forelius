import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_REQUIRED_ENVIRONMENT = ["ANTHROPIC_API_KEY"]


class ForeliusConfigurationError(Exception):
    pass


_initialized = False
_required_environment: list[str] = []


def initialize(required_environment: list[str] | None = None) -> None:
    global _initialized, _required_environment

    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)

    required = list(required_environment or DEFAULT_REQUIRED_ENVIRONMENT)
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        formatted_missing = ", ".join(missing)
        raise ForeliusConfigurationError(
            f"Missing required environment variable(s): {formatted_missing}"
        )

    _initialized = True
    _required_environment = required


def ensure_initialized() -> None:
    if not _initialized:
        initialize(_required_environment or DEFAULT_REQUIRED_ENVIRONMENT)
