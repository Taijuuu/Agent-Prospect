import requests
from typing import List, Dict, Optional
from loguru import logger
from config import EXPLORIUM_API_KEY

BASE_URL = "https://api.explorium.ai/v1"
HEADERS = {
    "API_KEY": EXPLORIUM_API_KEY,
    "Content-Type": "application/json"
}


class ExploRiumClient:

    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS

    def search_businesses(
        self,
        sectors: List[str],
        countries: List[str] = None,
        company_sizes: List[str] = None,
        page_size: int = 100,
        max_results: int = 1000
    ) -> List[Dict]:

        if not countries:
            countries = ["fr"]

        all_businesses = []

        for sector in sectors:
            effective_size = max(min(max_results, 5000), page_size)
            payload = {
                "mode": "full",
                "size": effective_size,
                "page_size": min(page_size, effective_size),
                "page": 1,
                "filters": {
                    "country_code": {"values": countries},
                    "google_category": {"values": [sector.lower()]}
                }
            }

            if company_sizes:
                payload["filters"]["company_size"] = {"values": company_sizes}

            try:
                response = requests.post(
                    f"{self.base_url}/businesses",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                if "data" in data:
                    all_businesses.extend(data["data"])
                    logger.info(f"Trouvé {len(data['data'])} entreprises pour {sector}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur Explorium pour {sector}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        logger.error(f"Détail erreur: {e.response.text}")
                    except:
                        pass
                continue

        deduplicated = self._deduplicate_by_domain(all_businesses)
        logger.info(f"Total après déduplication: {len(deduplicated)}")
        return deduplicated

    def enrich_prospects(
        self,
        business_ids: List[str],
        job_departments: List[str] = None
    ) -> List[Dict]:

        if not job_departments:
            job_departments = ["sales", "marketing", "management"]

        prospects = []

        for business_id in business_ids:
            payload = {
                "mode": "full",
                "size": 100,
                "page_size": 50,
                "page": 1,
                "filters": {
                    "business_id": {
                        "type": "includes",
                        "values": [business_id]
                    },
                    "job_department": {
                        "type": "includes",
                        "values": job_departments
                    },
                    "has_email": {
                        "type": "exists",
                        "value": True
                    }
                }
            }

            try:
                response = requests.post(
                    f"{self.base_url}/prospects",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                if "data" in data:
                    for prospect in data["data"]:
                        prospect["business_id"] = business_id
                        prospects.append(prospect)
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur enrichissement {business_id}: {e}")
                continue

        return prospects

    def get_contact_info(self, prospect_id: str) -> Optional[Dict]:

        try:
            payload = {"prospect_id": prospect_id}
            response = requests.post(
                f"{self.base_url}/prospects/contacts_information/enrich",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if "data" in data:
                return data["data"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur contact info {prospect_id}: {e}")

        return None

    def _deduplicate_by_domain(self, businesses: List[Dict]) -> List[Dict]:
        seen = set()
        dedup = []

        for business in businesses:
            domain = business.get("domain") or ""
            domain = domain.strip() if domain else ""
            if domain and domain not in seen:
                seen.add(domain)
                dedup.append(business)
            elif not domain:
                dedup.append(business)

        return dedup

    def run_full_search(
        self,
        sectors: List[str],
        countries: List[str] = None,
        max_per_sector: int = 100
    ) -> List[Dict]:

        businesses = self.search_businesses(
            sectors=sectors,
            countries=countries,
            max_results=max_per_sector
        )

        if not businesses:
            logger.warning("Aucune entreprise trouvée")
            return []

        business_ids = [b.get("business_id") for b in businesses if b.get("business_id")]
        logger.info(f"Enrichissement de {len(business_ids)} entreprises...")

        prospects = self.enrich_prospects(business_ids)

        for prospect in prospects:
            contact_info = self.get_contact_info(prospect.get("prospect_id"))
            if contact_info:
                prospect["email"] = contact_info.get("emails", [None])[0]
                prospect["phone"] = contact_info.get("phone_numbers")

        enriched_results = []
        for business in businesses:
            biz_prospects = [p for p in prospects if p.get("business_id") == business.get("business_id")]
            business["prospects"] = biz_prospects
            enriched_results.append(business)

        return enriched_results
