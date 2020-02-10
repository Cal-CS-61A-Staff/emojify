import os
from urllib.parse import urljoin

import requests

from db import connect_db

HOST = "https://auth.apps.cs61a.org"
CLIENT_NAME = "emojify"
AUTH_KEY = os.getenv("AUTH_KEY")


def query(endpoint, *, course, **kwargs):
    if course:
        with connect_db() as db:
            ret = db("SELECT auth_client, auth_secret FROM bot_data WHERE course = (%s)", [course]).fetchone()
            if ret:
                client_name, auth_key = ret
            else:
                raise KeyError
        return requests.post(
            urljoin(HOST, endpoint),
            json={
                "client_name": client_name,
                "secret": auth_key,
                **kwargs,
            },
        ).json()
    else:
        return requests.post(
            urljoin(HOST, endpoint),
            json={
                **kwargs,
            },
        ).json()

