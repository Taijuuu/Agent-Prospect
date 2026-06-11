import time
from typing import List, Dict

import requests
from loguru import logger

from config import GOOGLE_PLACES_API_KEY

AGGREGATEURS = {
    "pagesjaunes.fr", "travaux.com", "allovoisins.com", "habitatpresto.com",
    "houzz.fr", "comundo.fr", "mystartup.fr", "annuaire.fr", "justarrived.fr",
    "avisverifies.com", "tripadvisor.fr", "yelp.fr", "google.com", "facebook.com",
    "instagram.com", "leboncoin.fr", "lacentrale.fr", "guide-artisan.fr",
    "plombier-prix.fr", "artisanlocal.fr", "servicea.domicile.fr",
}

PLACE_DETAILS_FIELDS = "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total"


class ProspectFinder:

    def _geocoder(self, location: str) -> tuple[float, float] | None:
        """Convertit une ville en coordonnées GPS."""
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": location, "key": GOOGLE_PLACES_API_KEY},
            timeout=10
        )
        data = resp.json()
        if not data.get("results"):
            logger.warning(f"Impossible de géocoder: {location}")
            return None
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]

    def _place_details(self, place_id: str) -> dict:
        """Récupère téléphone + site web via Place Details."""
        try:
            resp = requests.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={
                    "place_id": place_id,
                    "fields": PLACE_DETAILS_FIELDS,
                    "key": GOOGLE_PLACES_API_KEY,
                    "language": "fr"
                },
                timeout=10
            )
            return resp.json().get("result", {})
        except Exception as e:
            logger.warning(f"Erreur Place Details pour {place_id}: {e}")
            return {}

    def _est_agregateur(self, url: str) -> bool:
        """Filtre les domaines agrégateurs connus."""
        if not url:
            return False
        from urllib.parse import urlparse
        domaine = urlparse(url).netloc.lower().replace("www.", "")
        return any(domaine == ag or domaine.endswith("." + ag) for ag in AGGREGATEURS)

    def search_google_places(
        self,
        query: str,
        location: str,
        radius_km: int = 30,
        max_results: int = 20
    ) -> List[Dict]:
        if not GOOGLE_PLACES_API_KEY:
            logger.warning("GOOGLE_PLACES_API_KEY non configuré, fallback sur DuckDuckGo")
            return self.search_via_serp(query, location, max_results)

        coords = self._geocoder(location)
        if not coords:
            return []
        lat, lng = coords

        results = []
        params = {
            "location": f"{lat},{lng}",
            "radius": radius_km * 1000,
            "keyword": query,
            "language": "fr",
            "key": GOOGLE_PLACES_API_KEY
        }

        while len(results) < max_results:
            resp = requests.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params=params,
                timeout=10
            )
            data = resp.json()

            for place in data.get("results", []):
                place_id = place.get("place_id", "")
                name = place.get("name", "").strip()
                if not name or not place_id:
                    continue

                # Place Details pour avoir téléphone + site web
                details = self._place_details(place_id)
                website = details.get("website", "")
                phone = details.get("formatted_phone_number", "")
                address = details.get("formatted_address", place.get("vicinity", ""))

                results.append({
                    "name": name,
                    "address": address,
                    "phone": phone,
                    "website": website,
                    "place_id": place_id,
                    "rating": details.get("rating", place.get("rating")),
                    "reviews": details.get("user_ratings_total", 0),
                    "city": location
                })

                time.sleep(0.3)

            next_token = data.get("next_page_token")
            if not next_token or len(results) >= max_results:
                break
            time.sleep(2)
            params = {"pagetoken": next_token, "key": GOOGLE_PLACES_API_KEY}

        return results[:max_results]

    def search_via_serp(self, query: str, location: str, num_results: int = 20) -> List[Dict]:
        """Fallback DuckDuckGo si pas de clé Google."""
        results = []
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                logger.error("ddgs non installé : pip install ddgs")
                return []

        try:
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(
                    f"{query} {location} artisan devis contact",
                    max_results=num_results * 3,
                    region="fr-fr"
                ))

            for r in ddg_results:
                website = r.get("href", "")
                if self._est_agregateur(website):
                    continue
                name = r.get("title", "").split(" - ")[0].split(" | ")[0].strip()
                if not name:
                    continue
                results.append({
                    "name": name,
                    "address": "",
                    "phone": "",
                    "website": website,
                    "place_id": "",
                    "city": location
                })
                if len(results) >= num_results:
                    break
        except Exception as e:
            logger.error(f"Erreur DuckDuckGo pour '{query}' à '{location}': {e}")

        return results

    def run_full_search(
        self,
        sectors: List[str],
        cities: List[str],
        max_per_combo: int = 20
    ) -> List[Dict]:
        all_results = []
        seen = set()

        for sector in sectors:
            for city in cities:
                logger.info(f"Recherche: {sector} à {city}")
                try:
                    if GOOGLE_PLACES_API_KEY:
                        results = self.search_google_places(sector, city, max_results=max_per_combo)
                    else:
                        results = self.search_via_serp(sector, city, num_results=max_per_combo)

                    for r in results:
                        key = (r["name"].lower().strip(), city.lower().strip())
                        if key not in seen:
                            seen.add(key)
                            r["industry"] = sector
                            r["city"] = city
                            all_results.append(r)

                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Erreur recherche {sector}/{city}: {e}")

        return all_results
