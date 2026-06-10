"""
Vérifie qu'un prospect n'a pas de site web en cherchant son nom sur le web.
Résultat stocké dans Prospect.notes au format JSON.
"""
import json
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from loguru import logger

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

import requests

# Domaines d'annuaires/réseaux sociaux — leur présence ne compte PAS comme "avoir un site"
DIRECTORY_DOMAINS = {
    'pagesjaunes.fr', 'google.com', 'google.fr', 'facebook.com', 'instagram.com',
    'twitter.com', 'linkedin.com', 'tripadvisor.fr', 'yelp.fr', 'yelp.com',
    'lafourchette.com', 'thefork.com', 'planity.com', 'doctolib.fr',
    'pages.fr', 'annuaires.fr', 'kompass.com', 'societe.com', 'infogreffe.fr',
    'leboncoin.fr', 'pagesjaunes.com', 'annuaire-mairie.fr', 'annuaire.fr',
    'youtube.com', 'tiktok.com', 'snapchat.com', 'pinterest.com',
    'maps.google.com', 'waze.com', 'mappy.com', 'viamichelin.fr',
    'pages24.fr', '118000.fr', '118712.fr', 'lespagesjaunes.fr',
    'pappers.fr', 'manageo.fr', 'verif.com', 'bizweb.fr',
}


def _domain_of(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace('www.', '').split(':')[0]
    except Exception:
        return ''


def _is_real_website(url: str) -> bool:
    domain = _domain_of(url)
    if not domain:
        return False
    return not any(d in domain for d in DIRECTORY_DOMAINS)


def _name_matches(company_name: str, text: str) -> bool:
    """Check if at least one meaningful word from the company name is in the text."""
    words = [w for w in company_name.lower().split() if len(w) > 3]
    if not words:
        return company_name.lower() in text.lower()
    return sum(1 for w in words if w in text.lower()) >= max(1, len(words) // 2)


def verify_web_presence(
    company_name: str,
    city: str,
    existing_url: str = '',
) -> dict:
    """
    Returns a dict:
    {
        "has_website": bool | None,  # None = inconclusive
        "found_url": str,
        "confidence": "high" | "medium" | "low",
        "reason": str,
        "checked_at": ISO string
    }
    """
    checked_at = datetime.utcnow().isoformat()

    # ── 1. Check URL already known from Pages Jaunes ─────────────────
    if existing_url and _is_real_website(existing_url):
        try:
            r = requests.head(existing_url, timeout=5, allow_redirects=True,
                              headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code < 400:
                return {
                    'has_website': True,
                    'found_url': existing_url,
                    'confidence': 'high',
                    'reason': f'URL connue et accessible ({r.status_code})',
                    'checked_at': checked_at,
                }
        except Exception:
            pass
        # URL known but not reachable — could be dead
        return {
            'has_website': True,
            'found_url': existing_url,
            'confidence': 'medium',
            'reason': 'URL connue mais inaccessible',
            'checked_at': checked_at,
        }

    # ── 2. Active web search ─────────────────────────────────────────
    queries = [
        f'"{company_name}" {city}',
        f'{company_name} {city} site officiel',
    ]

    found_url = ''
    found_in_directories_only = True

    try:
        with DDGS() as ddgs:
            for query in queries:
                results = list(ddgs.text(query, max_results=6, region='fr-fr'))
                for r in results:
                    url = r.get('href', '')
                    title = r.get('title', '')
                    body = r.get('body', '')
                    domain = _domain_of(url)

                    if not domain:
                        continue

                    if _is_real_website(url):
                        # Is this result actually about this company?
                        combined = f"{title} {body}".lower()
                        if _name_matches(company_name, combined):
                            found_url = url
                            found_in_directories_only = False
                            break
                    # If it's a directory result about them, note it
                time.sleep(0.8)
                if found_url:
                    break

    except Exception as e:
        logger.warning(f"verify_web_presence DDG error for '{company_name}': {e}")
        return {
            'has_website': None,
            'found_url': '',
            'confidence': 'low',
            'reason': f'Erreur recherche: {str(e)[:80]}',
            'checked_at': checked_at,
        }

    if found_url:
        # Double-check: actually visit the page
        try:
            resp = requests.get(found_url, timeout=5, allow_redirects=True,
                                headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code < 400:
                return {
                    'has_website': True,
                    'found_url': found_url,
                    'confidence': 'high',
                    'reason': f'Site trouvé et accessible: {_domain_of(found_url)}',
                    'checked_at': checked_at,
                }
        except Exception:
            pass
        return {
            'has_website': True,
            'found_url': found_url,
            'confidence': 'medium',
            'reason': f'URL trouvée mais non testée: {_domain_of(found_url)}',
            'checked_at': checked_at,
        }

    return {
        'has_website': False,
        'found_url': '',
        'confidence': 'medium',
        'reason': 'Aucun site trouvé hors annuaires',
        'checked_at': checked_at,
    }


def get_verification(notes_json: Optional[str]) -> Optional[dict]:
    """Parse verification data from the notes field."""
    if not notes_json:
        return None
    try:
        data = json.loads(notes_json)
        return data.get('verification')
    except Exception:
        return None


def set_verification(notes_json: Optional[str], verification: dict) -> str:
    """Merge verification data into the notes JSON string."""
    try:
        data = json.loads(notes_json) if notes_json else {}
    except Exception:
        data = {}
    data['verification'] = verification
    return json.dumps(data, ensure_ascii=False)
