import logging

logger = logging.getLogger(__name__)


def dispatch(task, *args):
    """Run a Celery task; never let a broker problem break a user request."""
    try:
        task.delay(*args)
    except Exception:  # pragma: no cover - broker outages
        logger.exception('Could not enqueue %s', getattr(task, 'name', task))
