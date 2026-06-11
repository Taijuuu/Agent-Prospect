import re
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Free/cheap website builders that are often low quality
FREE_BUILDERS = {
    "wix.com": "Wix (site gratuit)",
    "jimdo.com": "Jimdo (site gratuit)",
    "site123.com": "Site123",
    "weebly.com": "Weebly",
    "strikingly.com": "Strikingly",
    "godaddy.com/websites": "GoDaddy builder",
}

# Signals of an outdated design
OLD_TECH_SIGNALS = [
    ("application/x-shockwave-flash", "Flash (obsolète)"),
    (".swf", "Flash (obsolète)"),
    ("jquery-1.", "jQuery très ancien"),
    ("jquery-2.", "jQuery ancien"),
    ("bootstrap-2.", "Bootstrap 2 (obsolète)"),
    ("ie-only", "Optimisé IE uniquement"),
    ("msie", "Code IE legacy"),
    ("font-awesome/3.", "FontAwesome 3 (obsolète)"),
]


class WebsiteAnalyzer:

    def analyze(self, url: str, timeout: int = 6) -> dict:
        if not url:
            return {
                "score": 0,
                "label": "Aucun site web",
                "issues": ["Aucun site web détecté"],
                "positives": [],
                "cms": None,
                "load_time": None,
            }

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        score = 100
        issues = []
        positives = []
        cms = None
        load_time = None

        try:
            t0 = time.time()
            resp = requests.get(url, timeout=timeout, allow_redirects=True, headers=HEADERS)
            load_time = round(time.time() - t0, 2)

            if resp.status_code >= 400:
                return {
                    "score": 0,
                    "label": "Site hors ligne",
                    "issues": [f"Site inaccessible ({resp.status_code})"],
                    "positives": [],
                    "cms": None,
                    "load_time": load_time,
                }

            final_url = resp.url
            html = resp.text
            html_lower = html.lower()
            soup = BeautifulSoup(html, "lxml")

            # ── SSL ──────────────────────────────────────────────────────
            if final_url.startswith("https://"):
                positives.append("HTTPS activé")
            else:
                score -= 20
                issues.append("Pas de SSL/HTTPS")

            # ── Vitesse ──────────────────────────────────────────────────
            if load_time > 5:
                score -= 20
                issues.append(f"Site très lent ({load_time}s)")
            elif load_time > 3:
                score -= 10
                issues.append(f"Site lent ({load_time}s)")
            else:
                positives.append(f"Chargement rapide ({load_time}s)")

            # ── Responsive ───────────────────────────────────────────────
            viewport = soup.find("meta", attrs={"name": "viewport"})
            if viewport and "width=device-width" in (viewport.get("content") or ""):
                positives.append("Site responsive (mobile)")
            else:
                score -= 15
                issues.append("Non responsive (mauvais affichage mobile)")

            # ── SEO basique ───────────────────────────────────────────────
            title_tag = soup.find("title")
            if title_tag and title_tag.get_text(strip=True):
                positives.append("Balise title présente")
            else:
                score -= 5
                issues.append("Pas de balise title")

            desc = soup.find("meta", attrs={"name": "description"})
            if not desc or not desc.get("content"):
                score -= 5
                issues.append("Pas de meta description")

            # ── Âge du design (copyright) ─────────────────────────────────
            all_text = soup.get_text(" ")
            years_found = re.findall(r"\b(20\d{2})\b", all_text)
            if years_found:
                max_year = max(int(y) for y in years_found)
                age = datetime.now().year - max_year
                if age >= 5:
                    score -= 20
                    issues.append(f"Design obsolète (dernière mise à jour ~{max_year})")
                elif age >= 3:
                    score -= 10
                    issues.append(f"Design vieillissant ({max_year})")
                else:
                    positives.append(f"Contenu récent ({max_year})")

            # ── Technologies obsolètes ────────────────────────────────────
            for signal, label in OLD_TECH_SIGNALS:
                if signal in html_lower:
                    score -= 10
                    issues.append(label)
                    break

            # ── Analytics ────────────────────────────────────────────────
            has_ga = any(s in html_lower for s in ["google-analytics", "gtag(", "googletagmanager", "ga('send'"])
            has_pixel = "facebook.net/en_US/fbevents" in html_lower
            if has_ga or has_pixel:
                positives.append("Analytics en place")
            else:
                score -= 5
                issues.append("Pas de tracking/analytics")

            # ── Présence d'images ─────────────────────────────────────────
            imgs = soup.find_all("img")
            if len(imgs) < 2:
                score -= 5
                issues.append("Très peu d'images")

            # ── Pas de contact visible ────────────────────────────────────
            contact_signals = ["contact", "contactez", "nous joindre", "formulaire", "mailto:"]
            has_contact = any(s in html_lower for s in contact_signals)
            if not has_contact:
                score -= 5
                issues.append("Pas de page contact visible")

            # ── CMS / Builder ─────────────────────────────────────────────
            domain = urlparse(final_url).netloc.lower()
            for builder_domain, builder_name in FREE_BUILDERS.items():
                if builder_domain in domain or builder_domain in html_lower:
                    cms = builder_name
                    score -= 10
                    issues.append(f"Site créé avec {builder_name}")
                    break

            if not cms:
                if "wp-content" in html_lower or "wordpress" in html_lower:
                    cms = "WordPress"
                elif "joomla" in html_lower:
                    cms = "Joomla"
                    score -= 5
                    issues.append("Joomla (souvent obsolète)")
                elif "drupal" in html_lower:
                    cms = "Drupal"
                elif "shopify" in html_lower:
                    cms = "Shopify"
                    positives.append("Boutique Shopify")
                elif "squarespace" in html_lower:
                    cms = "Squarespace"

            # ── Score final ───────────────────────────────────────────────
            score = max(0, min(100, score))

        except requests.exceptions.SSLError:
            score -= 25
            issues.append("Certificat SSL invalide/expiré")
            score = max(0, score)
        except requests.exceptions.ConnectionError:
            return {
                "score": 0,
                "label": "Site inaccessible",
                "issues": ["Site inaccessible (connexion refusée)"],
                "positives": [],
                "cms": None,
                "load_time": None,
            }
        except requests.exceptions.Timeout:
            score -= 20
            issues.append(f"Site trop lent (timeout > {timeout}s)")
            score = max(0, score)
        except Exception as e:
            logger.warning(f"Erreur analyse {url}: {e}")
            return {
                "score": max(0, score),
                "label": _score_label(max(0, score)),
                "issues": issues + [f"Erreur: {str(e)[:60]}"],
                "positives": positives,
                "cms": cms,
                "load_time": load_time,
            }

        return {
            "score": score,
            "label": _score_label(score),
            "issues": issues,
            "positives": positives,
            "cms": cms,
            "load_time": load_time,
        }

    def is_worth_contacting(self, score: int) -> bool:
        """Score ≤ 65 = worth contacting (no site or mediocre site)."""
        return score <= 65


def _score_label(score: int) -> str:
    if score == 0:
        return "Aucun site"
    if score <= 30:
        return "Site très médiocre"
    if score <= 50:
        return "Site obsolète"
    if score <= 65:
        return "Site à améliorer"
    if score <= 80:
        return "Site correct"
    return "Bon site"
