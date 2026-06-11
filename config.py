import os
from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    """Read env var, stripping BOM and whitespace (Windows encoding safety)."""
    return os.getenv(name, default).lstrip("﻿").strip()


def _env_int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


TEST_MODE = _env("TEST_MODE", "False").lower() == "true"

ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
EXPLORIUM_API_KEY = _env("EXPLORIUM_API_KEY")
GOOGLE_PLACES_API_KEY = _env("GOOGLE_PLACES_API_KEY")

GMAIL_CREDENTIALS_FILE = _env("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = _env("GMAIL_TOKEN_FILE", "token.json")
GMAIL_SENDER_EMAIL = _env("GMAIL_SENDER_EMAIL")

DEFAULT_CITIES = [c.strip() for c in _env("DEFAULT_CITIES", "Paris").split(",")]
DEFAULT_SECTORS = [s.strip() for s in _env("DEFAULT_SECTORS", "restaurant,plombier,coiffeur").split(",")]
MAX_PROSPECTS_PER_RUN = _env_int("MAX_PROSPECTS_PER_RUN", 100)
MIN_WEBSITE_SCORE = _env_int("MIN_WEBSITE_SCORE", 65)

MY_NAME = _env("MY_NAME")
MY_TITLE = _env("MY_TITLE", "Développeur Web Freelance")
MY_PHONE = _env("MY_PHONE")
MY_WEBSITE = _env("MY_WEBSITE")

NOTIFICATION_EMAIL = _env("NOTIFICATION_EMAIL")
NTFY_TOPIC = _env("NTFY_TOPIC")
PUSHOVER_TOKEN = _env("PUSHOVER_TOKEN")
PUSHOVER_USER = _env("PUSHOVER_USER")

TIMEZONE = _env("TIMEZONE", "Europe/Paris")
FOLLOW_UP_DELAY_DAYS = _env_int("FOLLOW_UP_DELAY_DAYS", 5)
MAX_CONTACTS_PER_PROSPECT = _env_int("MAX_CONTACTS_PER_PROSPECT", 3)
DAILY_EMAIL_SEND_LIMIT = _env_int("DAILY_EMAIL_SEND_LIMIT", 50)

DATABASE_URL = _env("DATABASE_URL", "sqlite:///prospects.db")
STATE_FILE = "state.json"
LOG_FILE = "agent.log"

ALL_SECTORS = [
    "restaurant", "boulangerie", "plombier", "électricien",
    "coiffeur", "garage automobile", "fleuriste", "menuisier",
    "peintre en bâtiment", "serrurier", "traiteur", "photographe",
    "architecte", "expert-comptable", "avocat", "kiné", "dentiste"
]
