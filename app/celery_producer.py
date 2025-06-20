import logging

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

notifier_broker_url = settings.redis_url

notifier_queue_name = settings.notification_tasks_queue_name

notifier_celery_producer = Celery(
    'backend_to_notifier_producer',
    broker=notifier_broker_url,
    include=[
        'app.workers.celery_tasks.detailed_report_worker',
        'app.workers.celery_tasks.report_generator',
    ],
)

logger.info(
    f'Initialized Celery producer for Notifier. '
    f'Broker: {notifier_broker_url}, Queue: {notifier_queue_name}'
)

notifier_celery_producer.conf.beat_schedule = {
    'run-report-generation-every-monday': {
        'task': 'report_generator.run_report_generation_cycle',
        'schedule': crontab(hour=9, minute=0, day_of_week='monday'),
    },
}

NOTIFIER_TASK_NAME = 'src.notifier.tasks.send_notification'
