"""Analyse approfondie des sites web de prospects.

Pipeline en deux couches :
  1. Scraping HTML (requests + BeautifulSoup) → analyse par Claude (texte)
  2. Screenshots desktop/mobile (Playwright) → analyse par Claude Vision,
     uniquement si la couche 1 donne un score <= 6
"""

import base64
import json
import os
import random
import re
import time

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import ANTHROPIC_API_KEY

DEMO_MODE = os.getenv("DEMO_MODE", "False").lower() == "true"

HTTP_TIMEOUT = 10
PLAYWRIGHT_TIMEOUT_MS = 15000
MAX_TEXT_CHARS = 3000
SEUIL_ANALYSE_VISUELLE = 6

MODELE_HTML = "claude-haiku-4-5-20251001"
MODELE_VISION = "claude-sonnet-4-6"

PROMPT_HTML = """Tu es un expert en création de sites web et en UX. Analyse ce contenu HTML
et retourne UNIQUEMENT un JSON structuré (aucun texte autour) avec :
- score (int, 0-10) : qualité globale du site
- design_obsolete (bool)
- mobile_friendly (bool)
- seo_manquant (bool)
- https (bool)
- annee_estimee (int ou null) : estimation de l'année de création/dernière MAJ
- problemes (list[str]) : liste des problèmes détectés
- est_prospect (bool) : true si le site mérite une refonte
- resume (str) : 1 phrase résumant pourquoi c'est ou ce n'est pas un prospect"""

PROMPT_VISUEL = """Tu es un expert en design web et UX. Regarde ces deux screenshots (desktop et mobile)
d'un site web professionnel et retourne UNIQUEMENT un JSON (aucun texte autour) :
- score_visuel (int, 0-10)
- design_moderne (bool)
- responsive_ok (bool)
- problemes_visuels (list[str]) : ex: 'couleurs datées', 'mise en page désordonnée',
  'texte illisible sur mobile', 'images pixelisées'
- est_prospect (bool)
- resume_visuel (str) : 1 phrase"""


def _normaliser_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _parser_json_ia(texte: str) -> dict | None:
    """Extrait le JSON d'une réponse IA (tolère les fences markdown)."""
    texte = re.sub(r"^```(?:json)?|```$", "", texte.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", texte, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def scrape_site_content(url: str) -> dict | None:
    """Récupère le HTML, le texte visible et les métadonnées d'un site.

    Retourne None si le site est inaccessible.
    """
    url = _normaliser_url(url)

    try:
        start = time.time()
        response = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ProspectBot/1.0)"
        })
        load_time = time.time() - start
    except requests.exceptions.SSLError:
        try:
            start = time.time()
            response = requests.get(url.replace("https://", "http://"), timeout=HTTP_TIMEOUT)
            load_time = time.time() - start
        except Exception as e:
            logger.warning(f"Site inaccessible (SSL puis HTTP échoués) {url}: {e}")
            return None
    except Exception as e:
        logger.warning(f"Site inaccessible {url}: {e}")
        return None

    if response.status_code >= 400:
        logger.warning(f"Site {url} répond {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    texte_visible = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()[:MAX_TEXT_CHARS]

    title = soup.find("title")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_viewport = soup.find("meta", attrs={"name": "viewport"})
    footer = soup.find("footer")

    return {
        "url": response.url,
        "status_code": response.status_code,
        "load_time": round(load_time, 2),
        "https": response.url.startswith("https://"),
        "title": title.get_text(strip=True) if title else "",
        "meta_description": meta_desc.get("content", "") if meta_desc else "",
        "meta_viewport": meta_viewport.get("content", "") if meta_viewport else "",
        "footer": re.sub(r"\s+", " ", footer.get_text(separator=" ")).strip()[:500] if footer else "",
        "texte": texte_visible,
    }


def screenshot_site(url: str) -> dict | None:
    """Capture le site en desktop (1280x800) et mobile (390x844).

    Les screenshots restent en mémoire (bytes → base64), aucun fichier écrit.
    Retourne None si la capture échoue.
    """
    url = _normaliser_url(url)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright non installé : pip install playwright && playwright install chromium")
        return None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            screenshots = {}

            for nom, viewport in (("desktop", {"width": 1280, "height": 800}),
                                  ("mobile", {"width": 390, "height": 844})):
                page = browser.new_page(viewport=viewport)
                page.goto(url, timeout=PLAYWRIGHT_TIMEOUT_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                screenshots[nom] = base64.standard_b64encode(page.screenshot()).decode("ascii")
                page.close()

            browser.close()
            return screenshots
    except Exception as e:
        logger.warning(f"Screenshot raté pour {url}: {e}")
        return None


def _mock_analyser_html_ia(contenu: dict) -> dict:
    """Simulation IA pour démo : analyse HTML fictive réaliste."""
    url = contenu["url"]
    texte = contenu["texte"]

    # Heuristiques simples pour simuler une vraie analyse
    est_ancien = ("2015" in contenu.get("footer", "") or
                  "2016" in contenu.get("footer", "") or
                  "2017" in contenu.get("footer", ""))
    pas_viewport = not contenu.get("meta_viewport")
    lent = contenu.get("load_time", 0) > 3

    score = 8
    problemes = []

    if pas_viewport:
        score -= 2
        problemes.append("Non responsive (pas de meta viewport)")

    if est_ancien:
        score -= 3
        problemes.append("Copyright obsolète (2015-2017)")

    if lent:
        score -= 2
        problemes.append(f"Site lent ({contenu['load_time']}s)")

    if "contact" not in texte.lower():
        score -= 1
        problemes.append("Pas de section contact visible")

    if len(texte) < 500:
        score -= 1
        problemes.append("Contenu très maigre")

    score = max(0, min(10, score))

    return {
        "score": score,
        "design_obsolete": score <= 4,
        "mobile_friendly": not pas_viewport,
        "seo_manquant": len(problemes) > 2,
        "https": contenu.get("https", True),
        "annee_estimee": 2016 if est_ancien else 2020,
        "problemes": problemes,
        "est_prospect": score <= 6,
        "resume": f"Site {'datée' if est_ancien else 'moderne'}, {'non responsive' if pas_viewport else 'responsive'}, score {score}/10"
    }


def _mock_analyser_visuel_ia(screenshots: dict) -> dict:
    """Simulation Vision pour démo : analyse visuelle fictive."""
    score_visuel = random.randint(2, 7)
    problemes_visuels = []

    if score_visuel <= 4:
        problemes_visuels = [
            "Couleurs désaturées (années 2010)",
            "Mise en page désordonnée",
            "Texte trop petit sur mobile",
            "Images pixelisées ou compressées"
        ]
    elif score_visuel <= 6:
        problemes_visuels = [
            "Design un peu datée",
            "Contraste insuffisant",
            "Espacements incohérents"
        ]

    return {
        "score_visuel": score_visuel,
        "design_moderne": score_visuel >= 7,
        "responsive_ok": score_visuel >= 5,
        "problemes_visuels": problemes_visuels,
        "est_prospect": score_visuel <= 6,
        "resume_visuel": f"Design {'moderne et bien optimisé' if score_visuel >= 7 else 'datée, peu optimisé'}"
    }


def _client_anthropic():
    from anthropic import Anthropic
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def analyser_html_ia(contenu: dict) -> dict | None:
    """Couche 1 : analyse du contenu HTML par Claude (rapide, peu coûteuse)."""
    if DEMO_MODE:
        logger.info(f"[DEMO MODE] Analyse HTML simulée pour {contenu['url']}")
        time.sleep(0.5)
        return _mock_analyser_html_ia(contenu)

    donnees = (
        f"URL: {contenu['url']}\n"
        f"Code HTTP: {contenu['status_code']}\n"
        f"Temps de chargement: {contenu['load_time']}s\n"
        f"HTTPS: {contenu['https']}\n"
        f"Title: {contenu['title']}\n"
        f"Meta description: {contenu['meta_description']}\n"
        f"Meta viewport: {contenu['meta_viewport'] or 'ABSENT'}\n"
        f"Footer: {contenu['footer']}\n\n"
        f"Texte visible:\n{contenu['texte']}"
    )

    try:
        reponse = _client_anthropic().messages.create(
            model=MODELE_HTML,
            max_tokens=1024,
            system=PROMPT_HTML,
            messages=[{"role": "user", "content": donnees}],
        )
        resultat = _parser_json_ia(reponse.content[0].text)
        if not resultat:
            logger.warning(f"Réponse IA non parsable (HTML) pour {contenu['url']}")
        return resultat
    except Exception as e:
        logger.error(f"Erreur analyse HTML IA pour {contenu['url']}: {e}")
        return None


def analyser_visuel_ia(screenshots: dict) -> dict | None:
    """Couche 2 : analyse des screenshots par Claude Vision."""
    if DEMO_MODE:
        logger.info("[DEMO MODE] Analyse visuelle simulée")
        time.sleep(0.3)
        return _mock_analyser_visuel_ia(screenshots)

    blocs = [
        {"type": "text", "text": "Screenshot DESKTOP (1280x800) :"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshots["desktop"]}},
        {"type": "text", "text": "Screenshot MOBILE (390x844) :"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshots["mobile"]}},
    ]

    try:
        reponse = _client_anthropic().messages.create(
            model=MODELE_VISION,
            max_tokens=1024,
            system=PROMPT_VISUEL,
            messages=[{"role": "user", "content": blocs}],
        )
        resultat = _parser_json_ia(reponse.content[0].text)
        if not resultat:
            logger.warning("Réponse IA non parsable (visuel)")
        return resultat
    except Exception as e:
        logger.error(f"Erreur analyse visuelle IA: {e}")
        return None


def fusionner_analyses(analyse_html: dict, analyse_visuelle: dict | None) -> dict:
    """Fusionne les deux couches : 40% HTML + 60% visuel si dispo."""
    score_html = int(analyse_html.get("score", 0))
    problemes = list(analyse_html.get("problemes", []))

    if analyse_visuelle:
        score_visuel = int(analyse_visuelle.get("score_visuel", 0))
        score_final = round(0.4 * score_html + 0.6 * score_visuel)
        problemes += analyse_visuelle.get("problemes_visuels", [])
        est_prospect = bool(analyse_visuelle.get("est_prospect", analyse_html.get("est_prospect", False)))
        resume = f"{analyse_html.get('resume', '')} {analyse_visuelle.get('resume_visuel', '')}".strip()
    else:
        score_final = score_html
        est_prospect = bool(analyse_html.get("est_prospect", False))
        resume = analyse_html.get("resume", "")

    return {
        "score_final": score_final,
        "est_prospect": est_prospect,
        "problemes": problemes,
        "resume": resume,
    }


def analyser_site_complet(url: str) -> dict | None:
    """Pipeline complet pour un site : scraping → couche 1 → couche 2 si besoin → fusion.

    Retourne None si le site est inaccessible ou si l'analyse IA échoue.
    """
    contenu = scrape_site_content(url)
    if not contenu:
        return None

    analyse_html = analyser_html_ia(contenu)
    if not analyse_html:
        return None

    analyse_visuelle = None
    if int(analyse_html.get("score", 10)) <= SEUIL_ANALYSE_VISUELLE:
        screenshots = screenshot_site(url)
        if screenshots:
            analyse_visuelle = analyser_visuel_ia(screenshots)

    return fusionner_analyses(analyse_html, analyse_visuelle)
