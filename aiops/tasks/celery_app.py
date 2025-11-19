"""Celery application configuration."""

from celery import Celery
from kombu import Exchange, Queue
from aiops.core.config import get_config


def create_celery_app() -> Celery:
    """Create and configure Celery application.

    Returns:
        Configured Celery instance
    """
    config = get_config()

    # Get broker and result backend URLs
    broker_url = getattr(config, "celery_broker_url", "redis://localhost:6379/0")
    result_backend = getattr(config, "celery_result_backend", "redis://localhost:6379/0")

    # Create Celery app
    app = Celery(
        "aiops",
        broker=broker_url,
        backend=result_backend,
        include=[
            "aiops.tasks.agent_tasks",
            "aiops.tasks.monitoring_tasks",
            "aiops.tasks.maintenance_tasks",
        ],
    )

    # Configure Celery
    app.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Task routing
        task_default_queue="default",
        task_default_exchange="aiops",
        task_default_routing_key="default",
        # Result backend settings
        result_expires=3600,  # 1 hour
        result_persistent=True,
        # Task execution settings
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_time_limit=600,  # 10 minutes
        task_soft_time_limit=540,  # 9 minutes
        # Worker settings
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
    )

    # Define queues
    app.conf.task_queues = (
        Queue("default", Exchange("aiops"), routing_key="default"),
        Queue("agents", Exchange("aiops"), routing_key="agents.*"),
        Queue("monitoring", Exchange("aiops"), routing_key="monitoring.*"),
        Queue("maintenance", Exchange("aiops"), routing_key="maintenance.*"),
        Queue("priority", Exchange("aiops"), routing_key="priority.*", priority=10),
    )

    # Task routes
    app.conf.task_routes = {
        "aiops.tasks.agent_tasks.*": {"queue": "agents"},
        "aiops.tasks.monitoring_tasks.*": {"queue": "monitoring"},
        "aiops.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    }

    return app


# Global Celery app instance
celery_app = create_celery_app()


# Celery beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "cleanup-old-executions": {
        "task": "aiops.tasks.maintenance_tasks.cleanup_old_executions",
        "schedule": 3600.0,  # Every hour
    },
    "aggregate-costs": {
        "task": "aiops.tasks.monitoring_tasks.aggregate_daily_costs",
        "schedule": 86400.0,  # Every 24 hours
    },
    "health-check": {
        "task": "aiops.tasks.monitoring_tasks.system_health_check",
        "schedule": 300.0,  # Every 5 minutes
    },
}


if __name__ == "__main__":
    celery_app.start()
