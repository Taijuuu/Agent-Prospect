import base64
import email as email_lib
import json
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, GMAIL_SENDER_EMAIL

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:

    def __init__(self):
        self.service = None
        self.creds = None

    def authenticate(self):
        if os.path.exists(GMAIL_TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(GMAIL_TOKEN_FILE, "w") as f:
                f.write(self.creds.to_json())

        self.service = build("gmail", "v1", credentials=self.creds)
        logger.info("Gmail authentifié avec succès")
        return self.service

    def _get_service(self):
        if not self.service:
            self.authenticate()
        return self.service

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str,
        reply_to_thread_id: Optional[str] = None
    ) -> dict:
        service = self._get_service()

        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["From"] = GMAIL_SENDER_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        body = {"raw": raw}

        if reply_to_thread_id:
            body["threadId"] = reply_to_thread_id

        result = service.users().messages().send(userId="me", body=body).execute()
        return {
            "message_id": result.get("id"),
            "thread_id": result.get("threadId")
        }

    def get_replies_since(self, since_datetime: datetime) -> List[dict]:
        service = self._get_service()
        timestamp = int(since_datetime.timestamp())
        query = f"in:inbox after:{timestamp}"

        try:
            result = service.users().messages().list(
                userId="me", q=query, maxResults=50
            ).execute()
        except Exception as e:
            logger.error(f"Erreur récupération emails: {e}")
            return []

        messages = result.get("messages", [])
        replies = []

        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()

                headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
                thread_id = msg.get("threadId")
                body = self._extract_body(msg["payload"])
                received_at = datetime.fromtimestamp(int(msg["internalDate"]) / 1000)

                replies.append({
                    "thread_id": thread_id,
                    "message_id": msg["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "body": body,
                    "received_at": received_at
                })
            except Exception as e:
                logger.error(f"Erreur lecture message {msg_ref['id']}: {e}")

        return replies

    def _extract_body(self, payload: dict) -> str:
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            for part in payload["parts"]:
                result = self._extract_body(part)
                if result:
                    return result
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        return ""

    def mark_as_read(self, message_id: str):
        service = self._get_service()
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
        except Exception as e:
            logger.error(f"Erreur mark_as_read {message_id}: {e}")
