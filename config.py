import os
from dotenv import load_dotenv

load_dotenv()

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
EXPLORIUM_API_KEY = os.getenv("EXPLORIUM_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "")

DEFAULT_CITIES = [c.strip() for c in os.getenv("DEFAULT_CITIES", "Paris").split(",")]
DEFAULT_SECTORS = [s.strip() for s in os.getenv("DEFAULT_SECTORS", "restaurant,plombier,coiffeur").split(",")]
MAX_PROSPECTS_PER_RUN = int(os.getenv("MAX_PROSPECTS_PER_RUN", "100"))
MIN_WEBSITE_SCORE = int(os.getenv("MIN_WEBSITE_SCORE", "65"))

MY_NAME = os.getenv("MY_NAME", "")
MY_TITLE = os.getenv("MY_TITLE", "Développeur Web Freelance")
MY_PHONE = os.getenv("MY_PHONE", "")
MY_WEBSITE = os.getenv("MY_WEBSITE", "")

NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN", "")
PUSHOVER_USER = os.getenv("PUSHOVER_USER", "")

TIMEZONE = os.getenv("TIMEZONE", "Europe/Paris")
FOLLOW_UP_DELAY_DAYS = int(os.getenv("FOLLOW_UP_DELAY_DAYS", "5"))
MAX_CONTACTS_PER_PROSPECT = int(os.getenv("MAX_CONTACTS_PER_PROSPECT", "3"))
DAILY_EMAIL_SEND_LIMIT = int(os.getenv("DAILY_EMAIL_SEND_LIMIT", "50"))

DATABASE_URL = "sqlite:///prospects.db"
STATE_FILE = "state.json"
LOG_FILE = "agent.log"

ALL_SECTORS = [
    "restaurant", "boulangerie", "plombier", "électricien",
    "coiffeur", "garage automobile", "fleuriste", "menuisier",
    "peintre en bâtiment", "serrurier", "traiteur", "photographe",
    "architecte", "expert-comptable", "avocat", "kiné", "dentiste"
]
