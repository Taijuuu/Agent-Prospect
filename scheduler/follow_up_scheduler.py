from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import sessionmaker

from config import TIMEZONE
from database.models import get_engine
from database.crud import get_prospects_for_followup, get_stats
from email_agent.sender import send_follow_up_email
from email_agent.reply_monitor import ReplyMonitor
from email_agent.gmail_client import GmailClient
from notifications.notifier import Notifier


def _get_session():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _job_check_follow_ups():
    db = _get_session()
    try:
        prospects = get_prospects_for_followup(db)
        logger.info(f"Relances à envoyer: {len(prospects)}")
        for prospect in prospects:
            send_follow_up_email(db, prospect.id)
    except Exception as e:
        logger.error(f"Erreur job relances: {e}")
    finally:
        db.close()


def _job_check_replies():
    db = _get_session()
    gmail = GmailClient()
    notifier = Notifier(gmail_client=gmail, db=db)
    monitor = ReplyMonitor(db=db, notifier=notifier)
    try:
        monitor.check_for_replies()
    except Exception as e:
        logger.error(f"Erreur job réponses: {e}")
    finally:
        db.close()


def _job_daily_summary():
    db = _get_session()
    gmail = GmailClient()
    notifier = Notifier(gmail_client=gmail, db=db)
    try:
        stats = get_stats(db)
        notifier.notify_daily_summary(stats)
    except Exception as e:
        logger.error(f"Erreur job résumé quotidien: {e}")
    finally:
        db.close()


class FollowUpScheduler:

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=TIMEZONE)

    def start(self):
        self.scheduler.add_job(
            _job_check_follow_ups,
            CronTrigger(
                day_of_week="mon-fri",
                hour="8-18",
                minute="0",
                timezone=TIMEZONE
            ),
            id="check_follow_ups",
            name="Vérification des relances",
            replace_existing=True
        )

        self.scheduler.add_job(
            _job_check_replies,
            CronTrigger(
                day_of_week="mon-fri",
                hour="8-18",
                minute="0,30",
                timezone=TIMEZONE
            ),
            id="check_replies",
            name="Vérification des réponses",
            replace_existing=True
        )

        self.scheduler.add_job(
            _job_daily_summary,
            CronTrigger(
                day_of_week="mon-fri",
                hour="8",
                minute="0",
                timezone=TIMEZONE
            ),
            id="daily_summary",
            name="Résumé quotidien",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Scheduler démarré")

        for job in self.scheduler.get_jobs():
            logger.info(f"Job planifié: {job.name} — prochain: {job.next_run_time}")

    def stop(self):
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler arrêté")

    def get_jobs(self):
        return self.scheduler.get_jobs()
