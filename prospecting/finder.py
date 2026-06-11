import re
import time
import concurrent.futures
from typing import List, Dict
from urllib.parse import urljoin, urlparse
from loguru import logger

import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

try:
    from config import GOOGLE_PLACES_API_KEY
except ImportError:
    GOOGLE_PLACES_API_KEY = None

PLACE_DETAILS_FIELDS = "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total"

AGGREGATEURS = {
    "pagesjaunes.fr", "travaux.com", "allovoisins.com", "habitatpresto.com",
    "houzz.fr", "justacoté.fr", "justacote.com", "annuaire.com",
    "123pages.fr", "kompass.com", "societepages.fr", "societe.com",
    "manageo.fr", "infogreffe.fr", "pappers.fr", "verif.com",
    "tripadvisor.fr", "tripadvisor.com", "yelp.fr", "yelp.com",
    "google.com", "facebook.com", "linkedin.com",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'(?:0[1-9]|(?:\+|00)33\s?[1-9])(?:[\s.\-]?\d{2}){4}')
SKIP_EMAIL_PARTS = {
    'example', 'noreply', 'no-reply', 'test@', '@ex', 'email@', 'votre@',
    'your@', '.png', '.jpg', '.gif', 'sentry', '@2x', 'wix', 'squarespace',
    'wordpress', 'schema.org', 'w3.org',
}


def _clean_phone(raw: str) -> str:
    digits = re.sub(r'\D', '', raw)
    if digits.startswith('33') and len(digits) == 11:
        digits = '0' + digits[2:]
    if len(digits) == 10:
        return ' '.join(digits[i:i+2] for i in range(0, 10, 2))
    return raw.strip()


def _is_valid_email(e: str) -> bool:
    e = e.lower()
    return not any(s in e for s in SKIP_EMAIL_PARTS)


def extract_contact_from_url(url: str) -> Dict:
    """Fetch a URL (and its /contact page) and extract email + phone."""
    email, phone = '', ''
    if not url or not url.startswith('http'):
        return {'email': email, 'phone': phone}

    pages_html = []
    try:
        r = requests.get(url, timeout=7, headers=HEADERS, allow_redirects=True)
        if r.status_code < 400:
            pages_html.append(r.text)
            soup = BeautifulSoup(r.text, 'lxml')
            # Discover contact page link
            for a in soup.find_all('a', href=True):
                text = a.get_text(' ', strip=True).lower()
                href = a['href']
                if any(kw in text or kw in href.lower()
                       for kw in ['contact', 'nous joindre', 'joindre', 'coordonnées']):
                    full = urljoin(url, href)
                    if full != url and full.startswith('http'):
                        try:
                            cr = requests.get(full, timeout=5, headers=HEADERS)
                            if cr.status_code < 400:
                                pages_html.append(cr.text)
                        except Exception:
                            pass
                        break
    except Exception as e:
        logger.debug(f"fetch {url}: {e}")
        return {'email': email, 'phone': phone}

    for html in pages_html:
        if not email:
            found = EMAIL_RE.findall(html)
            valid = [e for e in found if _is_valid_email(e)]
            if valid:
                email = valid[0]
        if not phone:
            found = PHONE_RE.findall(html)
            if found:
                phone = _clean_phone(found[0])
        if email and phone:
            break

    return {'email': email, 'phone': phone}


def _est_agregateur(url: str) -> bool:
    """Renvoie True si l'URL appartient à un site agrégateur (annuaire, réseau social…)."""
    if not url:
        return False
    domain = urlparse(url).netloc.lower().lstrip("www.")
    return any(domain == ag or domain.endswith("." + ag) for ag in AGGREGATEURS)


class ProspectFinder:

    # ── Google Places API (v1 Text Search — website inclus, pas de Details) ──
    # Coût : $0.032 / appel (20 résultats) au lieu de $0.017 × N par Place Details
    FIELD_MASK = "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.id"

    def search_google_places(self, sector: str, city: str, max_results: int = 50) -> List[Dict]:
        """Text Search v1 — retourne website sans appel Place Details séparé."""
        results = []
        page_token = None
        url = "https://places.googleapis.com/v1/places:searchText"

        while len(results) < max_results:
            payload: Dict = {
                "textQuery": f"{sector} {city}",
                "languageCode": "fr",
                "pageSize": min(20, max_results - len(results)),
            }
            if page_token:
                payload["pageToken"] = page_token

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
                "X-Goog-FieldMask": self.FIELD_MASK,
            }

            try:
                r = requests.post(url, json=payload, headers=headers, timeout=10)
                data = r.json()

                if "error" in data:
                    logger.error(f"Places v1 error: {data['error'].get('message')}")
                    break

                for place in data.get("places", []):
                    website = place.get("websiteUri", "")
                    if _est_agregateur(website):
                        continue
                    name = place.get("displayName", {}).get("text", "")
                    if not name:
                        continue
                    results.append({
                        "name": name,
                        "phone": place.get("nationalPhoneNumber", ""),
                        "address": place.get("formattedAddress", ""),
                        "website": website,
                        "email": "",
                        "city": city,
                        "industry": sector,
                        "source": "google_places",
                        "rating": place.get("rating"),
                        "reviews": place.get("userRatingCount"),
                        "_place_id": place.get("id", ""),
                    })

                page_token = data.get("nextPageToken")
                if not page_token:
                    break
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Places v1 error: {e}")
                break

        logger.info(f"Google Places v1: {len(results)} résultats pour '{sector}' à '{city}'")
        return results[:max_results]

    def _enrich_phone_from_details(self, place_id: str) -> str:
        """Place Details uniquement pour le téléphone, sur les qualifiés seulement."""
        try:
            r = requests.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={"place_id": place_id, "fields": "formatted_phone_number", "key": GOOGLE_PLACES_API_KEY},
                timeout=8,
            )
            data = r.json()
            if data.get("status") == "OK":
                return data["result"].get("formatted_phone_number", "")
        except Exception:
            pass
        return ""

    # ── Pages Jaunes ────────────────────────────────────────────────────
    def search_pagesjaunes(self, sector: str, city: str, max_results: int = 50) -> List[Dict]:
        results = []
        page = 1
        session = requests.Session()
        session.headers.update(HEADERS)

        while len(results) < max_results:
            url = "https://www.pagesjaunes.fr/annuaire/cherche"
            params = {'quoi': sector, 'ou': city, 'page': page}
            try:
                resp = session.get(url, params=params, timeout=10)
                if resp.status_code == 403:
                    logger.warning("Pages Jaunes: accès refusé (403), fallback DDG")
                    break
                soup = BeautifulSoup(resp.text, 'lxml')

                items = soup.select('li.bi-item') or soup.select('article.bilink') or soup.select('div.bi-bloc')
                if not items:
                    break

                for item in items:
                    name_el = (item.select_one('.bi-denomination a') or
                               item.select_one('[class*="denomination"]') or
                               item.select_one('h3 a') or
                               item.select_one('a[class*="link"]'))
                    if not name_el:
                        continue
                    name = name_el.get_text(' ', strip=True)
                    if not name:
                        continue

                    phone_el = (item.select_one('.bi-phone') or
                                item.select_one('[class*="tel"]') or
                                item.select_one('[href^="tel:"]'))
                    phone = ''
                    if phone_el:
                        raw = phone_el.get('href', '') or phone_el.get_text()
                        phone = _clean_phone(raw.replace('tel:', ''))

                    addr_el = (item.select_one('.bi-address') or
                               item.select_one('[class*="address"]') or
                               item.select_one('[class*="street"]'))
                    address = addr_el.get_text(' ', strip=True) if addr_el else ''

                    web_el = item.select_one('a[href*="http"]')
                    website = ''
                    if web_el:
                        href = web_el.get('href', '')
                        if 'pagesjaunes' not in href:
                            website = href

                    results.append({
                        'name': name,
                        'phone': phone,
                        'address': address,
                        'website': website,
                        'email': '',
                        'city': city,
                        'industry': sector,
                        'source': 'pagesjaunes',
                    })

                page += 1
                time.sleep(1.2)

            except Exception as e:
                logger.error(f"Pages Jaunes error p{page}: {e}")
                break

        return results[:max_results]

    # ── DuckDuckGo text fallback ─────────────────────────────────────────
    def search_via_ddg(self, sector: str, city: str, max_results: int = 50) -> List[Dict]:
        results = []
        seen = set()
        queries = [
            f"{sector} {city} téléphone adresse",
            f"{sector} artisan {city} contact",
            f'"{sector}" "{city}"',
        ]

        try:
            with DDGS() as ddgs:
                for q in queries:
                    if len(results) >= max_results:
                        break
                    try:
                        hits = list(ddgs.text(q, max_results=20, region='fr-fr'))
                        for r in hits:
                            title = r.get('title', '')
                            name = title.split(' - ')[0].split(' | ')[0].strip()
                            if not name or name.lower() in seen:
                                continue
                            seen.add(name.lower())
                            results.append({
                                'name': name,
                                'phone': '',
                                'address': '',
                                'website': r.get('href', ''),
                                'email': '',
                                'city': city,
                                'industry': sector,
                                'source': 'duckduckgo',
                            })
                        time.sleep(1.5)
                    except Exception as e:
                        logger.warning(f"DDG query '{q}': {e}")
        except Exception as e:
            logger.error(f"DDG init: {e}")

        return results[:max_results]

    # ── Contact enrichment (concurrent) ─────────────────────────────────
    def enrich_contacts(self, results: List[Dict], max_workers: int = 6) -> List[Dict]:
        to_enrich = [(i, r['website']) for i, r in enumerate(results)
                     if r.get('website') and not r.get('email')]

        if not to_enrich:
            return results

        logger.info(f"Enrichissement contact pour {len(to_enrich)} résultats...")

        def fetch(item):
            idx, url = item
            return idx, extract_contact_from_url(url)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(fetch, item): item[0] for item in to_enrich}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    idx, contact = fut.result(timeout=20)
                    if contact.get('email') and not results[idx]['email']:
                        results[idx]['email'] = contact['email']
                    if contact.get('phone') and not results[idx]['phone']:
                        results[idx]['phone'] = contact['phone']
                except Exception:
                    pass

        return results

    # ── Website scoring (concurrent) ─────────────────────────────────────
    def score_websites(self, results: List[Dict], max_workers: int = 8) -> List[Dict]:
        """Run WebsiteAnalyzer on every result concurrently."""
        from prospecting.website_analyzer import WebsiteAnalyzer
        analyzer = WebsiteAnalyzer()

        def analyze(item):
            idx, url = item
            if not url:
                return idx, {"score": 0, "label": "Aucun site", "issues": ["Aucun site web"], "positives": [], "cms": None, "load_time": None}
            return idx, analyzer.analyze(url)

        to_analyze = [(i, r.get('website', '')) for i, r in enumerate(results)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(analyze, item): item[0] for item in to_analyze}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    idx, analysis = fut.result(timeout=15)
                    results[idx]['website_score'] = analysis['score']
                    results[idx]['website_label'] = analysis.get('label', '')
                    results[idx]['website_issues'] = analysis.get('issues', [])
                    results[idx]['website_positives'] = analysis.get('positives', [])
                    results[idx]['website_cms'] = analysis.get('cms')
                    results[idx]['load_time'] = analysis.get('load_time')
                except Exception:
                    results[idx]['website_score'] = 0
                    results[idx]['website_issues'] = ['Analyse impossible']

        return results

    # ── Main entry point ─────────────────────────────────────────────────
    def run_full_search(
        self,
        sectors: List[str],
        cities: List[str],
        max_per_combo: int = 20,
        no_website_only: bool = False,
        max_score: int = 65,
    ) -> List[Dict]:
        """
        Trouve exactement max_per_combo prospects QUALIFIÉS (mauvais site ou sans site).
        On cherche jusqu'à 4× plus de candidats pour atteindre le quota demandé.
        """
        # On cherche beaucoup plus large pour avoir assez de qualifiés après filtrage
        fetch_count = min(max_per_combo * 4, 100)
        all_candidates = []
        seen: set = set()

        for sector in sectors:
            for city in cities:
                logger.info(f"Recherche: {sector} à {city} (cible={max_per_combo}, fetch={fetch_count})")

                if GOOGLE_PLACES_API_KEY:
                    results = self.search_google_places(sector, city, fetch_count)
                else:
                    results = self.search_pagesjaunes(sector, city, fetch_count)
                    if not results:
                        logger.info("Pages Jaunes vide, fallback DuckDuckGo")
                        results = self.search_via_ddg(sector, city, fetch_count)

                for r in results:
                    key = (r['name'].lower().strip(), city.lower())
                    if key not in seen:
                        seen.add(key)
                        all_candidates.append(r)

                time.sleep(0.8)

        logger.info(f"Analyse des sites web pour {len(all_candidates)} candidats...")
        all_candidates = self.score_websites(all_candidates)

        # Filtre qualité site
        if no_website_only:
            qualified = [r for r in all_candidates if not r.get('website') or r.get('website_score', 0) == 0]
        else:
            qualified = [r for r in all_candidates if r.get('website_score', 0) <= max_score]

        logger.info(f"{len(qualified)}/{len(all_candidates)} qualifiés — on en retourne {min(len(qualified), max_per_combo)}")

        # On tronque au quota demandé
        qualified = qualified[:max_per_combo]

        # Enrichissement contacts uniquement sur les qualifiés retenus
        qualified = self.enrich_contacts(qualified)

        # Pour les qualifiés sans téléphone (Places v1 ne le retourne pas toujours),
        # appel Place Details ciblé — payant mais seulement sur les 20 retenus
        if GOOGLE_PLACES_API_KEY:
            for p in qualified:
                if not p.get("phone") and p.get("_place_id"):
                    p["phone"] = self._enrich_phone_from_details(p["_place_id"])

        return qualified
