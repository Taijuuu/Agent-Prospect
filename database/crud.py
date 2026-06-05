from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from database.models import Prospect, EmailLog, ProspectStatus, EmailDirection


def create_prospect(db: Session, data: dict) -> Prospect:
    prospect = Prospect(**data)
    db.add(prospect)
    db.commit()
    db.refresh(prospect)
    return prospect


def get_prospect(db: Session, prospect_id: int) -> Optional[Prospect]:
    return db.query(Prospect).filter(Prospect.id == prospect_id).first()


def get_prospects(
    db: Session,
    status: Optional[ProspectStatus] = None,
    city: Optional[str] = None,
    score_max: Optional[int] = None,
    limit: int = 100
) -> List[Prospect]:
    q = db.query(Prospect)
    if status:
        q = q.filter(Prospect.status == status)
    if city:
        q = q.filter(Prospect.city.ilike(f"%{city}%"))
    if score_max is not None:
        q = q.filter(Prospect.website_score <= score_max)
    return q.limit(limit).all()


def get_prospects_for_followup(db: Session) -> List[Prospect]:
    now = datetime.utcnow()
    return db.query(Prospect).filter(
        Prospect.status == ProspectStatus.contacted,
        Prospect.next_follow_up_at <= now,
        Prospect.contact_count < 3
    ).all()


def update_prospect(db: Session, prospect_id: int, data: dict) -> Optional[Prospect]:
    prospect = get_prospect(db, prospect_id)
    if not prospect:
        return None
    for key, value in data.items():
        setattr(prospect, key, value)
    db.commit()
    db.refresh(prospect)
    return prospect


def prospect_exists(db: Session, company_name: str, city: str) -> bool:
    return db.query(Prospect).filter(
        Prospect.company_name.ilike(company_name),
        Prospect.city.ilike(city)
    ).first() is not None


def create_email_log(db: Session, data: dict) -> EmailLog:
    log = EmailLog(**data)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_sent_emails_with_thread(db: Session) -> List[EmailLog]:
    return db.query(EmailLog).filter(
        EmailLog.direction == EmailDirection.sent,
        EmailLog.gmail_thread_id.isnot(None)
    ).all()


def get_prospect_by_thread(db: Session, thread_id: str) -> Optional[Prospect]:
    log = db.query(EmailLog).filter(
        EmailLog.gmail_thread_id == thread_id,
        EmailLog.direction == EmailDirection.sent
    ).first()
    if log:
        return get_prospect(db, log.prospect_id)
    return None


def count_emails_sent_today(db: Session) -> int:
    today = datetime.utcnow().date()
    return db.query(EmailLog).filter(
        EmailLog.direction == EmailDirection.sent,
        EmailLog.sent_at >= datetime(today.year, today.month, today.day)
    ).count()


def get_stats(db: Session) -> dict:
    total = db.query(Prospect).count()
    by_status = {}
    for status in ProspectStatus:
        by_status[status.value] = db.query(Prospect).filter(
            Prospect.status == status
        ).count()
    return {"total": total, "by_status": by_status}
