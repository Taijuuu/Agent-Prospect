import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Enum as SAEnum, create_engine
)
from sqlalchemy.orm import declarative_base, relationship
from config import DATABASE_URL

Base = declarative_base()


class ProspectStatus(enum.Enum):
    new = "new"
    contacted = "contacted"
    replied = "replied"
    converted = "converted"
    unsubscribed = "unsubscribed"
    bounced = "bounced"


class EmailDirection(enum.Enum):
    sent = "sent"
    received = "received"


class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    industry = Column(String(100))
    address = Column(String(500))
    city = Column(String(100))
    phone = Column(String(50))
    email = Column(String(255))
    website_url = Column(String(500))
    website_score = Column(Integer, default=0)
    website_issues = Column(Text)
    source = Column(String(50))
    status = Column(SAEnum(ProspectStatus), default=ProspectStatus.new)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_contacted_at = Column(DateTime)
    next_follow_up_at = Column(DateTime)
    contact_count = Column(Integer, default=0)
    notes = Column(Text)

    emails = relationship("EmailLog", back_populates="prospect")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=True)
    gmail_message_id = Column(String(255))
    gmail_thread_id = Column(String(255))
    direction = Column(SAEnum(EmailDirection), nullable=False)
    subject = Column(String(500))
    body = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_reply = Column(Boolean, default=False)

    prospect = relationship("Prospect", back_populates="emails")


def get_engine():
    url = DATABASE_URL
    # Vercel Postgres envoie une URL postgres:// — SQLAlchemy 1.4+ exige postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return create_engine(url)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine
