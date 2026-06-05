import json
from datetime import datetime
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Integer, create_engine, text
from database.models import Base, get_engine
from config import DATABASE_URL

class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True)
    template_type = Column(String, unique=True, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailTemplate {self.template_type}>"


def init_template_db():
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_or_create_templates(
    db: Session,
    template_type: str,
    default_subject: str,
    default_body: str
) -> dict:

    template = db.query(EmailTemplate).filter_by(template_type=template_type).first()

    if template:
        return {
            "id": template.id,
            "type": template_type,
            "subject": template.subject,
            "body": template.body,
            "is_new": False
        }

    new_template = EmailTemplate(
        template_type=template_type,
        subject=default_subject,
        body=default_body
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    return {
        "id": new_template.id,
        "type": template_type,
        "subject": new_template.subject,
        "body": new_template.body,
        "is_new": True
    }


def update_template(db: Session, template_type: str, subject: str, body: str) -> bool:
    template = db.query(EmailTemplate).filter_by(template_type=template_type).first()

    if not template:
        return False

    template.subject = subject
    template.body = body
    template.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"Template '{template_type}' mis à jour")
    return True


def get_template(db: Session, template_type: str) -> Optional[dict]:
    template = db.query(EmailTemplate).filter_by(template_type=template_type).first()

    if not template:
        return None

    return {
        "id": template.id,
        "type": template_type,
        "subject": template.subject,
        "body": template.body
    }


def list_all_templates(db: Session) -> list:
    templates = db.query(EmailTemplate).all()

    return [
        {
            "id": t.id,
            "type": t.template_type,
            "subject": t.subject,
            "body": t.body,
            "updated_at": t.updated_at.isoformat()
        }
        for t in templates
    ]
