import json
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from config import STATE_FILE
from database.crud import (
    create_email_log, get_prospect_by_thread,
    get_sent_emails_with_thread, update_prospect
)
from database.models import EmailDirection, ProspectStatus
from email_agent.gmail_client import GmailClient

STOP_KEYWORDS = ["stop", "désinscription", "desinscription", "désabonnement", "desabonnement", "ne pas recontacter"]


def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, default=str)


def _is_stop_request(body: str) -> bool:
    body_lower = body.lower().strip()
    return any(kw in body_lower for kw in STOP_KEYWORDS)


class ReplyMonitor:

    def __init__(self, db: Session, notifier=None):
        self.db = db
        self.notifier = notifier
        self.gmail = GmailClient()

    def check_for_replies(self):
        state = _load_state()
        last_check_str = state.get("last_reply_check")

        if last_check_str:
            try:
                last_check = datetime.fromisoformat(last_check_str)
            except Exception:
                last_check = datetime.utcnow() - timedelta(hours=24)
        else:
            last_check = datetime.utcnow() - timedelta(hours=24)

        try:
            replies = self.gmail.get_replies_since(last_check)
        except Exception as e:
            logger.error(f"Erreur récupération réponses: {e}")
            return

        known_threads = {
            log.gmail_thread_id
            for log in get_sent_emails_with_thread(self.db)
        }

        for reply in replies:
            thread_id = reply.get("thread_id")
            if not thread_id or thread_id not in known_threads:
                continue

            prospect = get_prospect_by_thread(self.db, thread_id)
            if not prospect:
                continue

            body = reply.get("body", "")

            create_email_log(self.db, {
                "prospect_id": prospect.id,
                "gmail_message_id": reply["message_id"],
                "gmail_thread_id": thread_id,
                "direction": EmailDirection.received,
                "subject": reply.get("subject", ""),
                "body": body,
                "sent_at": reply.get("received_at", datetime.utcnow()),
                "is_reply": True
            })

            if _is_stop_request(body):
                update_prospect(self.db, prospect.id, {
                    "status": ProspectStatus.unsubscribed,
                    "next_follow_up_at": None
                })
                logger.info(f"Désinscription de {prospect.company_name}")
            else:
                update_prospect(self.db, prospect.id, {
                    "status": ProspectStatus.replied,
                    "next_follow_up_at": None
                })
                logger.info(f"Réponse reçue de {prospect.company_name}")

                if self.notifier:
                    try:
                        self.notifier.notify_reply(
                            {"company_name": prospect.company_name, "city": prospect.city},
                            reply
                        )
                    except Exception as e:
                        logger.error(f"Erreur notification: {e}")

            try:
                self.gmail.mark_as_read(reply["message_id"])
            except Exception:
                pass

        state["last_reply_check"] = datetime.utcnow().isoformat()
        _save_state(state)
        logger.info(f"Vérification des réponses terminée ({len(replies)} emails analysés)")
