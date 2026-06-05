import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import GOOGLE_PLACES_API_KEY, HUNTER_IO_API_KEY

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
GENERIC_PREFIXES = {"noreply", "no-reply", "donotreply", "mailer", "bounce", "support", "admin"}

CONTACT_PATHS = ["/contact", "/contact-us", "/nous-contacter", "/contactez-nous", "/a-propos", "/about"]


class ContactExtractor:

    def _extract_emails_from_html(self, html: str, base_url: str = "") -> list:
        emails = []

        for match in re.finditer(r'href=["\']mailto:([^"\'?\s]+)', html, re.IGNORECASE):
            emails.append(match.group(1).split("?")[0].strip())

        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ")
        for match in EMAIL_REGEX.finditer(text):
            emails.append(match.group(0))

        for match in EMAIL_REGEX.finditer(html):
            emails.append(match.group(0))

        unique = list(dict.fromkeys(e.lower() for e in emails if "@" in e and "." in e.split("@")[1]))
        return unique

    def _is_generic(self, email: str) -> bool:
        prefix = email.split("@")[0].lower()
        return any(gen in prefix for gen in GENERIC_PREFIXES)

    def extract_email_from_website(self, url: str) -> Optional[str]:
        if not url:
            return None

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        headers = {"User-Agent": "Mozilla/5.0 (compatible; ProspectBot/1.0)"}
        all_emails = []

        urls_to_try = [url] + [url.rstrip("/") + p for p in CONTACT_PATHS]

        for try_url in urls_to_try[:4]:
            try:
                resp = requests.get(try_url, timeout=5, headers=headers, allow_redirects=True)
                if resp.status_code == 200:
                    found = self._extract_emails_from_html(resp.text, try_url)
                    all_emails.extend(found)
            except Exception:
                continue

        non_generic = [e for e in all_emails if not self._is_generic(e)]
        if non_generic:
            return non_generic[0]

        if all_emails:
            return all_emails[0]

        return None

    def extract_from_google_places(self, place_id: str) -> dict:
        if not GOOGLE_PLACES_API_KEY or not place_id:
            return {"website": "", "phone": "", "email": ""}

        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            resp = requests.get(url, params={
                "place_id": place_id,
                "fields": "website,formatted_phone_number",
                "key": GOOGLE_PLACES_API_KEY,
                "language": "fr"
            }, timeout=10)
            data = resp.json().get("result", {})
            return {
                "website": data.get("website", ""),
                "phone": data.get("formatted_phone_number", ""),
                "email": ""
            }
        except Exception as e:
            logger.error(f"Erreur Google Places Details {place_id}: {e}")
            return {"website": "", "phone": "", "email": ""}

    def find_email_via_hunter(self, domain: str) -> Optional[str]:
        if not HUNTER_IO_API_KEY or not domain:
            return None

        try:
            resp = requests.get("https://api.hunter.io/v2/domain-search", params={
                "domain": domain,
                "api_key": HUNTER_IO_API_KEY,
                "limit": 1
            }, timeout=10)
            data = resp.json()
            emails = data.get("data", {}).get("emails", [])
            if emails:
                return emails[0].get("value")
        except Exception as e:
            logger.error(f"Erreur Hunter.io {domain}: {e}")

        return None
