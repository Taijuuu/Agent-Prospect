from datetime import datetime, timedelta

import requests
from loguru import logger

from config import (
    NOTIFICATION_EMAIL, NTFY_TOPIC,
    PUSHOVER_TOKEN, PUSHOVER_USER
)


class Notifier:

    def __init__(self, gmail_client=None, db=None):
        self.gmail_client = gmail_client
        self.db = db

    def notify_reply(self, prospect: dict, email_received: dict):
        company = prospect.get("company_name", "Inconnu")
        city = prospect.get("city", "")
        body_excerpt = email_received.get("body", "")[:300]
        thread_id = email_received.get("thread_id", "")

        subject = f"🎯 Réponse de {company} !"
        body = f"""Bonne nouvelle ! {company} ({city}) a répondu à votre email de prospection.

Extrait de la réponse :
---
{body_excerpt}
---

Thread Gmail ID : {thread_id}
Reçu le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}
"""

        self._send_email_notification(subject, body)
        self._send_ntfy(subject, f"{company} a répondu !")
        self._send_pushover(f"{company} a répondu !", f"Nouvelle réponse de {company} ({city})")

    def notify_daily_summary(self, stats: dict):
        if not self.db:
            return

        subject = f"📊 Résumé quotidien - {datetime.now().strftime('%d/%m/%Y')}"

        yesterday = datetime.utcnow() - timedelta(days=1)

        body = f"""Résumé de votre agent de prospection :

Total prospects en base : {stats.get('total', 0)}
Répartition par statut :
"""
        for status, count in stats.get("by_status", {}).items():
            body += f"  - {status}: {count}\n"

        body += f"\nDate : {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        self._send_email_notification(subject, body)

    def _send_email_notification(self, subject: str, body: str):
        if not NOTIFICATION_EMAIL or not self.gmail_client:
            return
        try:
            self.gmail_client.send_email(
                to=NOTIFICATION_EMAIL,
                subject=subject,
                body_html=body.replace("\n", "<br>"),
                body_text=body
            )
            logger.info(f"Notification email envoyée: {subject}")
        except Exception as e:
            logger.error(f"Erreur notification email: {e}")

    def _send_ntfy(self, title: str, message: str):
        if not NTFY_TOPIC:
            return
        try:
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=message.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": "urgent",
                    "Tags": "email,money_with_wings"
                },
                timeout=5
            )
        except Exception as e:
            logger.error(f"Erreur ntfy: {e}")

    def _send_pushover(self, title: str, message: str):
        if not PUSHOVER_TOKEN or not PUSHOVER_USER:
            return
        try:
            requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": PUSHOVER_TOKEN,
                    "user": PUSHOVER_USER,
                    "title": title,
                    "message": message
                },
                timeout=5
            )
        except Exception as e:
            logger.error(f"Erreur Pushover: {e}")
