from celery import Celery
from app.core import settings

celery_app = Celery(
    "commerce_worker",
    broker=settings.REDIS_URL or "redis://localhost:6379/0",
    backend=settings.REDIS_URL or "redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="send_order_confirmation_email")
def send_order_confirmation_email(order_id: int, customer_email: str | None = None):
    email = customer_email or f"customer_order_{order_id}@example.com"
    print(f"[celery] sending confirmation email for order #{order_id} to {email}")
    return {"order_id": order_id, "status": "sent"}
