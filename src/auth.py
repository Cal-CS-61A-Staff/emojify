from os import getenv
from urllib.parse import urljoin

import requests

HOST = "https://auth.apps.cs61a.org"


def query(endpoint, *, course, **kwargs):
    return requests.post(
        urljoin(HOST, endpoint),
        json={
            "client_name": getenv("AUTH_CLIENT"),
            "secret": getenv("AUTH_KEY"),
            "course": course,
            **kwargs,
        },
    ).json()
