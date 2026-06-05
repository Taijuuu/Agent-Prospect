import json
from typing import Optional

import anthropic
from loguru import logger

from config import ANTHROPIC_API_KEY, MY_NAME, MY_TITLE, MY_PHONE, MY_WEBSITE

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Tu es un assistant copywriting expert en prospection B2B pour une agence web freelance.
Tu rédiges des emails de prospection courts, humains, non-commerciaux et efficaces.
Ton style : direct, bienveillant, sans bullshit marketing.
Tu écris en français. Tu ne dépasses jamais 150 mots.
Tu mets en valeur 1 problème concret que l'entreprise a avec son site actuel (ou l'absence de site),
et tu proposes une solution simple sans vendre agressivement."""


def _call_claude(prompt: str) -> Optional[dict]:
    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        text = next((b.text for b in response.content if b.type == "text"), "")

        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON invalide depuis Claude: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur Claude API: {e}")
        return None


def generate_first_email(prospect: dict) -> Optional[dict]:
    website_info = prospect.get("website_url") or "aucun site web"
    issues = prospect.get("website_issues", "[]")
    if isinstance(issues, str):
        try:
            issues = json.loads(issues)
        except Exception:
            issues = []
    issues_str = ", ".join(issues) if issues else "site absent"

    signature = f"{MY_NAME} - {MY_TITLE}"
    if MY_PHONE:
        signature += f"\n{MY_PHONE}"
    if MY_WEBSITE:
        signature += f"\n{MY_WEBSITE}"

    prompt = f"""Génère un email de prospection pour :
- Entreprise : {prospect.get('company_name', '')}
- Secteur : {prospect.get('industry', '')}
- Ville : {prospect.get('city', '')}
- Site web actuel : {website_info}
- Problèmes détectés : {issues_str}

L'email doit :
- Commencer par 'Bonjour,'
- Mentionner précisément leur situation (pas de site / site obsolète / problème spécifique détecté)
- Montrer que j'ai regardé leur activité
- Proposer un appel de 15 minutes sans engagement
- Inclure cette phrase : "Si vous ne souhaitez pas être recontacté, répondez simplement 'Stop'."
- Se terminer par cette signature exacte :
{signature}
- Avoir un objet d'email accrocheur (max 50 caractères)

Réponds UNIQUEMENT avec un JSON valide :
{{"subject": "...", "body": "..."}}"""

    return _call_claude(prompt)


def generate_follow_up_email(prospect: dict, first_email_body: str) -> Optional[dict]:
    signature = f"{MY_NAME} - {MY_TITLE}"
    if MY_PHONE:
        signature += f"\n{MY_PHONE}"
    if MY_WEBSITE:
        signature += f"\n{MY_WEBSITE}"

    prompt = f"""Génère un email de relance court et bienveillant pour :
- Entreprise : {prospect.get('company_name', '')}
- Secteur : {prospect.get('industry', '')}
- Ville : {prospect.get('city', '')}

Mon premier email disait :
{first_email_body[:300]}...

La relance doit :
- Être très courte (50-80 mots max)
- Rappeler doucement le premier contact
- Rester non-agressif et humain
- Inclure : "Si vous ne souhaitez pas être recontacté, répondez simplement 'Stop'."
- Se terminer par :
{signature}

Réponds UNIQUEMENT avec un JSON valide :
{{"subject": "...", "body": "..."}}"""

    return _call_claude(prompt)


def generate_email_templates() -> dict:
    signature = f"{MY_NAME} - {MY_TITLE}"
    if MY_PHONE:
        signature += f"\n{MY_PHONE}"
    if MY_WEBSITE:
        signature += f"\n{MY_WEBSITE}"

    no_website_prompt = f"""Tu es expert en prospection B2B pour une agence web freelance.
Génère UN template d'email pour contacter des entreprises qui N'ONT PAS DE SITE WEB.

L'email doit :
- Commencer par 'Bonjour,'
- Reconnaître qu'ils n'ont pas de site web (sans juger)
- Montrer que ça peut affecter leur visibilité
- Proposer un appel de 15 minutes pour discuter (sans engagement)
- Inclure : "Si vous ne souhaitez pas être recontacté, répondez simplement 'Stop'."
- Se terminer par cette signature :
{signature}
- Être réutilisable avec {{COMPANY_NAME}} comme placeholder

Objet d'email : accrocheur, max 50 caractères, avec {{COMPANY_NAME}} si utile

Réponds UNIQUEMENT avec un JSON valide :
{{"subject": "...", "body": "..."}}"""

    bad_website_prompt = f"""Tu es expert en prospection B2B pour une agence web freelance.
Génère UN template d'email pour contacter des entreprises qui ONT UN SITE WEB MÉDIOCRE/OBSOLÈTE.

L'email doit :
- Commencer par 'Bonjour,'
- Reconnaître qu'ils ont un site mais qu'il pourrait être amélioré
- Mentionner spécifiquement des problèmes courants : pas responsive, lent, design vieillot, peu visible sur Google
- Proposer un appel de 15 minutes pour diagnostiquer les problèmes (sans engagement)
- Inclure : "Si vous ne souhaitez pas être recontacté, répondez simplement 'Stop'."
- Se terminer par cette signature :
{signature}
- Être réutilisable avec {{COMPANY_NAME}} comme placeholder

Objet d'email : accrocheur, max 50 caractères, avec {{COMPANY_NAME}} si utile

Réponds UNIQUEMENT avec un JSON valide :
{{"subject": "...", "body": "..."}}"""

    logger.info("Génération des templates par Claude...")
    no_website = _call_claude(no_website_prompt)
    bad_website = _call_claude(bad_website_prompt)

    return {
        "no_website": no_website or {"subject": "Erreur", "body": "Impossible de générer"},
        "bad_website": bad_website or {"subject": "Erreur", "body": "Impossible de générer"}
    }
