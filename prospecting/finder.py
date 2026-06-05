import time
from typing import List, Dict, Optional

import requests
from duckduckgo_search import DDGS
from loguru import logger

from config import GOOGLE_PLACES_API_KEY


class ProspectFinder:

    def search_google_places(
        self,
        query: str,
        location: str,
        radius_km: int = 50,
        max_results: int = 100
    ) -> List[Dict]:
        if not GOOGLE_PLACES_API_KEY:
            logger.warning("GOOGLE_PLACES_API_KEY non configuré, fallback sur DuckDuckGo")
            return self.search_via_serp(query, location, max_results)

        results = []
        radius_m = radius_km * 1000

        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geo_resp = requests.get(geocode_url, params={
            "address": location,
            "key": GOOGLE_PLACES_API_KEY
        }, timeout=10)
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            logger.warning(f"Impossible de géocoder: {location}")
            return []

        lat = geo_data["results"][0]["geometry"]["location"]["lat"]
        lng = geo_data["results"][0]["geometry"]["location"]["lng"]

        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": radius_m,
            "keyword": query,
            "language": "fr",
            "key": GOOGLE_PLACES_API_KEY
        }

        while len(results) < max_results:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            for place in data.get("results", []):
                results.append({
                    "name": place.get("name", ""),
                    "address": place.get("vicinity", ""),
                    "phone": "",
                    "website": "",
                    "place_id": place.get("place_id", ""),
                    "types": place.get("types", []),
                    "city": location
                })

            next_token = data.get("next_page_token")
            if not next_token or len(results) >= max_results:
                break

            time.sleep(2)
            params = {"pagetoken": next_token, "key": GOOGLE_PLACES_API_KEY}

        return results[:max_results]

    def search_via_serp(self, query: str, location: str, num_results: int = 50) -> List[Dict]:
        results = []
        search_query = f"{query} {location} contact"

        try:
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(search_query, max_results=num_results, region="fr-fr"))

            for r in ddg_results:
                name = r.get("title", "").split(" - ")[0].split(" | ")[0].strip()
                if not name:
                    continue
                results.append({
                    "name": name,
                    "address": "",
                    "phone": "",
                    "website": r.get("href", ""),
                    "place_id": "",
                    "types": [query],
                    "city": location
                })
        except Exception as e:
            logger.error(f"Erreur DuckDuckGo pour '{query}' à '{location}': {e}")

        return results

    def filter_no_website(self, results: List[Dict]) -> List[Dict]:
        return [r for r in results if not r.get("website")]

    def run_full_search(
        self,
        sectors: List[str],
        cities: List[str],
        max_per_combo: int = 50
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
