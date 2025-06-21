import logging

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

notifier_broker_url = settings.redis_url

notifier_queue_name = settings.notification_tasks_queue_name

notifier_celery_producer = Celery(
    'backend_to_notifier_producer',
    broker=notifier_broker_url,
    include=[],
)

logger.info(
    f'Initialized Celery producer for Notifier. '
    f'Broker: {notifier_broker_url}, Queue: {notifier_queue_name}'
)


NOTIFIER_TASK_NAME = 'src.notifier.tasks.send_notification'
