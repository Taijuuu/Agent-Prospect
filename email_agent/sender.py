import json
import time
from datetime import date, datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from config import DAILY_EMAIL_SEND_LIMIT, FOLLOW_UP_DELAY_DAYS, STATE_FILE
from database.crud import (
    count_emails_sent_today, create_email_log, get_prospect,
    get_sent_emails_with_thread, update_prospect
)
from database.models import EmailDirection, ProspectStatus
from email_agent.email_writer import generate_first_email, generate_follow_up_email
from email_agent.gmail_client import GmailClient

gmail = GmailClient()


def add_business_days(start_date: date, days: int) -> date:
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, default=str)


def _check_daily_limit(db: Session) -> bool:
    sent_today = count_emails_sent_today(db)
    if sent_today >= DAILY_EMAIL_SEND_LIMIT:
        logger.warning(f"Limite journalière atteinte ({sent_today}/{DAILY_EMAIL_SEND_LIMIT})")
        return False
    return True


def send_prospecting_email(db: Session, prospect_id: int) -> bool:
    if not _check_daily_limit(db):
        return False

    prospect = get_prospect(db, prospect_id)
    if not prospect:
        logger.error(f"Prospect {prospect_id} introuvable")
        return False

    if not prospect.email:
        logger.warning(f"Pas d'email pour {prospect.company_name}")
        return False

    prospect_dict = {
        "company_name": prospect.company_name,
        "industry": prospect.industry,
        "city": prospect.city,
        "website_url": prospect.website_url,
        "website_issues": prospect.website_issues
    }

    email_data = generate_first_email(prospect_dict)
    if not email_data:
        logger.error(f"Impossible de générer l'email pour {prospect.company_name}")
        return False

    subject = email_data.get("subject", "Votre présence en ligne")
    body = email_data.get("body", "")
    body_html = body.replace("\n", "<br>")

    try:
        result = gmail.send_email(
            to=prospect.email,
            subject=subject,
            body_html=body_html,
            body_text=body
        )
    except Exception as e:
        logger.error(f"Erreur envoi email à {prospect.email}: {e}")
        return False

    create_email_log(db, {
        "prospect_id": prospect_id,
        "gmail_message_id": result["message_id"],
        "gmail_thread_id": result["thread_id"],
        "direction": EmailDirection.sent,
        "subject": subject,
        "body": body,
        "sent_at": datetime.utcnow(),
        "is_reply": False
    })

    follow_up_date = add_business_days(date.today(), FOLLOW_UP_DELAY_DAYS)
    update_prospect(db, prospect_id, {
        "status": ProspectStatus.contacted,
        "last_contacted_at": datetime.utcnow(),
        "next_follow_up_at": datetime.combine(follow_up_date, datetime.min.time()),
        "contact_count": (prospect.contact_count or 0) + 1
    })

    logger.info(f"Email envoyé à {prospect.company_name} ({prospect.email})")
    time.sleep(60)
    return True


def send_follow_up_email(db: Session, prospect_id: int) -> bool:
    if not _check_daily_limit(db):
        return False

    prospect = get_prospect(db, prospect_id)
    if not prospect:
        return False

    if (prospect.contact_count or 0) >= 3:
        update_prospect(db, prospect_id, {
            "status": ProspectStatus.unsubscribed,
            "next_follow_up_at": None
        })
        return False

    sent_logs = get_sent_emails_with_thread(db)
    prospect_logs = [l for l in sent_logs if l.prospect_id == prospect_id]
    first_body = prospect_logs[0].body if prospect_logs else ""

    prospect_dict = {
        "company_name": prospect.company_name,
        "industry": prospect.industry,
        "city": prospect.city,
    }

    email_data = generate_follow_up_email(prospect_dict, first_body)
    if not email_data:
        return False

    subject = email_data.get("subject", "Re: Votre site web")
    body = email_data.get("body", "")
    body_html = body.replace("\n", "<br>")

    thread_id = prospect_logs[0].gmail_thread_id if prospect_logs else None

    try:
        result = gmail.send_email(
            to=prospect.email,
            subject=subject,
            body_html=body_html,
            body_text=body,
            reply_to_thread_id=thread_id
        )
    except Exception as e:
        logger.error(f"Erreur relance {prospect.email}: {e}")
        return False

    create_email_log(db, {
        "prospect_id": prospect_id,
        "gmail_message_id": result["message_id"],
        "gmail_thread_id": result["thread_id"],
        "direction": EmailDirection.sent,
        "subject": subject,
        "body": body,
        "sent_at": datetime.utcnow(),
        "is_reply": True
    })

    follow_up_date = add_business_days(date.today(), FOLLOW_UP_DELAY_DAYS)
    update_prospect(db, prospect_id, {
        "last_contacted_at": datetime.utcnow(),
        "next_follow_up_at": datetime.combine(follow_up_date, datetime.min.time()),
        "contact_count": (prospect.contact_count or 0) + 1
    })

    logger.info(f"Relance envoyée à {prospect.company_name}")
    time.sleep(60)
    return True
