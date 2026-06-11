"""Qualification des prospects en deux catégories :
  - sans_site : pas de site web du tout
  - site_mauvaise_qualite : site existant mais qui mérite une refonte

Orchestration du pipeline d'analyse + export CSV/JSON.
"""

import csv
import json
import time
from datetime import datetime

from loguru import logger
from rich.console import Console

from prospecting.site_analyzer import analyser_site_complet

DELAI_ENTRE_ANALYSES = 1.5

console = Console()


def qualifier_prospect(business: dict) -> dict:
    """Qualifie un prospect : sans site / site à refondre / site correct."""
    nom = business.get("name", "").strip()
    url = business.get("website", "").strip()

    base = {
        "nom": nom,
        "url": url,
        "telephone": business.get("phone", ""),
        "adresse": business.get("address", ""),
    }

    if not url:
        return {
            **base,
            "score_final": 0,
            "est_prospect": True,
            "type": "sans_site",
            "problemes": ["Aucun site web"],
            "resume": "Aucun site web : prospect direct.",
        }

    analyse = analyser_site_complet(url)

    if analyse is None:
        # Site inaccessible ou analyse impossible : opportunité quand même
        return {
            **base,
            "score_final": 0,
            "est_prospect": True,
            "type": "site_mauvaise_qualite",
            "problemes": ["Site inaccessible ou analyse impossible"],
            "resume": "Le site ne répond pas correctement : refonte ou nouveau site à proposer.",
        }

    return {
        **base,
        "score_final": analyse["score_final"],
        "est_prospect": analyse["est_prospect"],
        "type": "site_mauvaise_qualite" if analyse["est_prospect"] else "site_correct",
        "problemes": analyse["problemes"],
        "resume": analyse["resume"],
    }


def qualifier_tous_les_prospects(businesses: list[dict]) -> list[dict]:
    """Qualifie tous les prospects, avec un délai entre chaque analyse."""
    resultats = []
    total = len(businesses)

    for i, business in enumerate(businesses, 1):
        nom = business.get("name", "?")
        console.print(f"[dim][{i}/{total}][/dim] Analyse de [bold]{nom}[/bold]...")
        try:
            resultats.append(qualifier_prospect(business))
        except Exception as e:
            logger.error(f"Erreur qualification {nom}: {e}")
            continue
        if i < total:
            time.sleep(DELAI_ENTRE_ANALYSES)

    return resultats


def exporter_resultats(resultats: list[dict], base_filename: str | None = None) -> tuple[str, str]:
    """Filtre les prospects qualifiés, trie par score croissant, exporte CSV + JSON.

    Retourne les chemins (csv, json) des fichiers créés.
    """
    prospects = [r for r in resultats if r.get("est_prospect")]
    prospects.sort(key=lambda r: r["score_final"])

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base = base_filename or f"prospects_qualifies_{timestamp}"
    chemin_csv = f"{base}.csv"
    chemin_json = f"{base}.json"

    with open(chemin_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nom", "url", "telephone", "adresse",
                                               "score_final", "type", "problemes", "resume"])
        writer.writeheader()
        for p in prospects:
            writer.writerow({**{k: p[k] for k in ("nom", "url", "telephone", "adresse",
                                                  "score_final", "type", "resume")},
                             "problemes": " | ".join(p["problemes"])})

    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump(prospects, f, ensure_ascii=False, indent=2)

    sans_site = sum(1 for p in prospects if p["type"] == "sans_site")
    mauvaise_qualite = sum(1 for p in prospects if p["type"] == "site_mauvaise_qualite")

    console.print(f"\n[bold green]{len(prospects)} prospects qualifiés[/bold green] "
                  f"(sur {len(resultats)} analysés)")
    console.print(f"  • [yellow]{sans_site}[/yellow] sans site web")
    console.print(f"  • [yellow]{mauvaise_qualite}[/yellow] avec site de mauvaise qualité")
    console.print(f"  • Export: [bold]{chemin_csv}[/bold] et [bold]{chemin_json}[/bold]")

    return chemin_csv, chemin_json
