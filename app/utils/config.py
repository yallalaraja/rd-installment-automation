import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


def _get_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid integer.") from exc


@dataclass(frozen=True)
class Settings:
    agent_id: str
    password: str
    base_url: str
    headless: bool
    timeout: int
    default_accounts_file: Path
    default_log_file: Path


settings = Settings(
    agent_id=os.getenv("AGENT_ID", ""),
    password=os.getenv("PASSWORD", ""),
    base_url=os.getenv("BASE_URL", "https://dopagent.indiapost.gov.in"),
    headless=_get_bool("HEADLESS", default=False),
    timeout=_get_int("TIMEOUT", default=30),
    default_accounts_file=DATA_DIR / "accounts.csv",
    default_log_file=LOG_DIR / "rd_automation.log",
)

DEFAULT_ACCOUNTS_FILE = settings.default_accounts_file
DEFAULT_LOG_FILE = settings.default_log_file
BASE_URL = settings.base_url
LOGIN_URL = settings.base_url
DEFAULT_HEADLESS = settings.headless
DEFAULT_TIMEOUT = settings.timeout
AGENT_ID = settings.agent_id
PASSWORD = settings.password
