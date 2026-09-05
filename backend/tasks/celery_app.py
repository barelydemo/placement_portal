"""Celery instance — broker and result backend both on Redis.

Tasks need a Flask application context (DB session, config), so every task runs
inside one via `FlaskTask`. The app is built lazily, once per worker process,
which also keeps this module import-safe: `backend.app` imports routes, which
import these tasks.
"""

from celery import Celery, Task
from celery.schedules import crontab

from backend.config import Config


class FlaskTask(Task):
    """Base task that runs inside a Flask application context."""

    _flask_app = None

    @property
    def flask_app(self):
        if FlaskTask._flask_app is None:
            from backend.app import create_app  # imported late to avoid a cycle

            FlaskTask._flask_app = create_app()
        return FlaskTask._flask_app

    def __call__(self, *args, **kwargs):
        with self.flask_app.app_context():
            return self.run(*args, **kwargs)


celery_app = Celery(
    "ppa",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    task_cls=FlaskTask,
)

celery_app.conf.update(
    # Keep Celery 5.x behaviour of retrying the broker connection on startup
    # (silences the 6.0 deprecation warning shown on worker boot).
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    # Modules the worker must import so tasks get registered.
    include=["backend.tasks.jobs"],
    beat_schedule={
        "daily-deadline-reminders": {
            "task": "ppa.send_daily_reminders",
            "schedule": crontab(
                hour=Config.REMINDER_HOUR, minute=Config.REMINDER_MINUTE
            ),
        },
        "monthly-activity-report": {
            "task": "ppa.send_monthly_report",
            "schedule": crontab(
                day_of_month="1",
                hour=Config.MONTHLY_REPORT_HOUR,
                minute=Config.MONTHLY_REPORT_MINUTE,
            ),
        },
    },
)
