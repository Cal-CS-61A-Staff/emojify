from functools import wraps

import requests
from flask import request, abort, jsonify

from db import connect_db
from env import API_SECRET


def api_secure(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if request.json["secret"] != API_SECRET:
            abort(401)
        return f(*args, **kwargs)
    return wrapped


def create_api_client(app):
    @app.route("/api/<course>/list_channels", methods=["POST"])
    @api_secure
    def list_channels(course):
        with connect_db() as db:
            bot_token, = db(
                "SELECT bot_access_token FROM bot_data WHERE course = (%s)",
                [course],
            ).fetchone()

        resp = requests.post(
            "https://slack.com/api/users.conversations",
            {"exclude_archived": True, "types": "public_channel,private_channel"},
            headers={"Authorization": "Bearer {}".format(bot_token)},
        ).json()

        return jsonify(resp["channels"])

    @app.route("/api/<course>/post_message", methods=["POST"])
    @api_secure
    def post_message(course):
        with connect_db() as db:
            bot_token, = db(
                "SELECT bot_access_token FROM bot_data WHERE course = (%s)",
                [course],
            ).fetchone()

        requests.post(
            "https://slack.com/api/chat.postMessage",
            json={
                "channel": request.json["channel"],
                "text": request.json["message"],
            },
            headers={"Authorization": "Bearer {}".format(bot_token)},
        )

        return ""
