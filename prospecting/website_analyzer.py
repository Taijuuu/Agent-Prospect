import json
import re
import ssl
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger


class WebsiteAnalyzer:

    def analyze(self, url: str) -> dict:
        if not url:
            return {"score": 0, "issues": ["Aucun site web"], "cms": None}

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        score = 100
        issues = []
        cms = None

        try:
            start = time.time()
            response = requests.get(url, timeout=5, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ProspectBot/1.0)"
            })
            load_time = time.time() - start

            if response.status_code >= 400:
                return {"score": 0, "issues": [f"Site hors ligne (erreur {response.status_code})"], "cms": None}

            if not url.startswith("https://") and not response.url.startswith("https://"):
                score -= 20
                issues.append("Pas de SSL/HTTPS")

            if load_time > 3:
                score -= 15
                issues.append(f"Site lent ({load_time:.1f}s)")

            soup = BeautifulSoup(response.text, "lxml")

            if not soup.find("meta", attrs={"name": "viewport"}):
                score -= 15
                issues.append("Non responsive (pas de meta viewport)")

            if not soup.find("title") or not soup.find("title").text.strip():
                score -= 5
                issues.append("Balise title manquante")

            if not soup.find("meta", attrs={"name": "description"}):
                score -= 5
                issues.append("Meta description manquante")

            footer_text = ""
            footer = soup.find("footer")
            if footer:
                footer_text = footer.get_text()
            years = re.findall(r"\b(20\d{2})\b", footer_text)
            if years:
                max_year = max(int(y) for y in years)
                if datetime.now().year - max_year > 3:
                    score -= 10
                    issues.append(f"Copyright obsolète ({max_year})")
            elif footer_text:
                score -= 10
                issues.append("Année de copyright introuvable")

            html_lower = response.text.lower()

            if "google-analytics" not in html_lower and "gtag" not in html_lower and "googletagmanager" not in html_lower:
                score -= 5
                issues.append("Pas de Google Analytics")

            if "object" in html_lower and ("application/x-shockwave-flash" in html_lower or ".swf" in html_lower):
                score -= 10
                issues.append("Technologies obsolètes (Flash)")

            if "wordpress" in html_lower or "wp-content" in html_lower:
                cms = "WordPress"
            elif "joomla" in html_lower:
                cms = "Joomla"
            elif "drupal" in html_lower:
                cms = "Drupal"
            elif "wix" in html_lower:
                cms = "Wix"
            elif "squarespace" in html_lower:
                cms = "Squarespace"

        except requests.exceptions.SSLError:
            score -= 20
            issues.append("Certificat SSL invalide")
            try:
                response = requests.get(url.replace("https://", "http://"), timeout=5)
                soup = BeautifulSoup(response.text, "lxml")
            except Exception:
                pass
        except requests.exceptions.ConnectionError:
            return {"score": 0, "issues": ["Site inaccessible"], "cms": None}
        except requests.exceptions.Timeout:
            score -= 15
            issues.append("Site trop lent (timeout > 5s)")
        except Exception as e:
            logger.warning(f"Erreur analyse {url}: {e}")
            return {"score": max(0, score), "issues": issues + [f"Erreur: {str(e)[:50]}"], "cms": cms}

        return {"score": max(0, score), "issues": issues, "cms": cms}

    def is_worth_contacting(self, score: int) -> bool:
        return score <= 65
