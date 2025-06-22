import os
import logging
import requests

LOGGER = logging.getLogger(__name__)
WEBHOOK_URL = os.getenv("PEGASUS_BACKEND_URL")


def send_webhook(data: dict):
    """Send a POST request to the backend with *data*."""
    if not WEBHOOK_URL:
        LOGGER.warning("No backend URL configured")
        return
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=5)
        response.raise_for_status()
        LOGGER.info("Notification sent: %s", response.status_code)
    except Exception as exc:
        LOGGER.error("Notification error: %s", exc)
