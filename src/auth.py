import os
from urllib.parse import urljoin

import requests

HOST = "https://auth.apps.cs61a.org"
CLIENT_NAME = "emojify"
AUTH_KEY = os.getenv("AUTH_KEY")


def query(endpoint, **kwargs):
    return requests.post(
        urljoin(HOST, endpoint),
        json={
            "client_name": CLIENT_NAME,
            "secret": AUTH_KEY,
            **kwargs,
        },
    ).json()
