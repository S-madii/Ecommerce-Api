from celery import Celery
from app.core import settings

# 1. Initialize Celery with Redis as the Message Broker
celery_app = Celery(
    "commerce_worker",
    broker=settings.REDIS_URL or "redis://localhost:6379/0",
    backend=settings.REDIS_URL or "redis://localhost:6379/0",
)

# 2. Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


# 3. Define the Background Task
@celery_app.task(name="send_order_confirmation_email")
def send_order_confirmation_email(order_id: int, customer_email: str):
    """Simulates sending an order confirmation email in the background."""
    print(f"[CELERY WORKER] 📧 Sending confirmation email for Order #{order_id} to {customer_email}...")
    # In real production, call SendGrid, Postmark, or SMTP here!
    print(f"[CELERY WORKER] ✅ Email successfully sent for Order #{order_id}!")
    return {"order_id": order_id, "status": "sent"}
