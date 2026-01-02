import requests
from django.conf import settings


def send_webpush(title, message, url="/"):
    """
    Send a push notification using Webpushr
    """

    if not settings.WEBPUSHR_API_KEY or not settings.WEBPUSHR_AUTH_TOKEN:
        print("Webpushr credentials not configured")
        return False

    payload = {
        "title": title,
        "message": message,
        "target_url": url,
    }

    headers = {
        "webpushrKey": settings.WEBPUSHR_API_KEY,
        "webpushrAuthToken": settings.WEBPUSHR_AUTH_TOKEN,
        "Content-Type": "application/json",
    }

    response = requests.post(
        settings.WEBPUSHR_BASE_URL,
        json=payload,
        headers=headers,
        timeout=5
    )

    return response.status_code == 200
