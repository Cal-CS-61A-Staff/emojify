import json
import os
import traceback

import requests
from flask import request, jsonify

from config import store_user_token, REJECTED, get_user_token, UNABLE
from db import connect_db
from emoji_integration import EmojiIntegration
from env import CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN_61A
from golink_integration import GoLinkIntegration
from integration import combine_integrations
from piazza_integration import PiazzaIntegration
from promotions import make_promo_block
from security import slack_signed


def create_slack_client(app):
    @app.route("/oauth")
    @slack_signed
    def oauth():
        if not request.args["code"]:
            return jsonify({"Error": "sadcat"}), 500
        resp = requests.post(
            "https://slack.com/api/oauth.v2.access",
            {
                "code": request.args["code"],
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        if resp.status_code == 200:
            store_user_token(
                resp.json()["authed_user"]["id"], resp.json()["authed_user"]["access_token"]
            )
            return jsonify(resp.json())
        return jsonify({"Error": "sadcat"}), 500

    @app.route("/interactive_handler", methods=["POST"])
    @slack_signed
    def handler():
        payload = json.loads(request.form["payload"])
        if "actions" not in payload or "value" not in payload["actions"][0]:
            return ""
        action = payload["actions"][0]["value"]
        user_id = payload["user"]["id"]
        if action == "activate":
            requests.post(payload["response_url"], json={
                "text": ":robot_face: Activated! While we can't update your previous message (:crying_cat_face:), all your future messages will be made awesome!",
                "replace_original": "true",
            })
        elif action == "maybe_later":
            requests.post(payload["response_url"], json={
                "text": "Alright, I'll ask you again later. Or visit slack.apps.cs61a.org to activate this bot manually!!",
                "replace_original": "true",
            })
        elif action == "never_ask_again":
            with connect_db() as db:
                db("INSERT INTO silenced_users VALUES (%s)", (user_id,))
            requests.post(payload["response_url"], json={
                "text": "Understood. If you ever change your mind, visit slack.apps.cs61a.org to activate this bot!",
                "replace_original": "true",
            })

        return ""

    @app.route("/message_send", methods=["POST"])
    @slack_signed
    def message_send():
        d = request.json
        try:
            if "challenge" in d:
                return
            event = d["event"]

            if event["type"] == "channel_created":
                print(requests.post(
                    "https://slack.com/api/conversations.join",
                    json={
                        "channel": event["channel"]["id"],
                    },
                    headers={"Authorization": "Bearer {}".format(ACCESS_TOKEN_61A)},
                ).json())
                return

            token = get_user_token(event["user"])
            if token is REJECTED:
                return
            if "edited" in event:
                return
            if "subtype" in event:
                return

            combined_integration = combine_integrations(
                [EmojiIntegration, PiazzaIntegration, GoLinkIntegration]
            )(event["text"], token if token is not UNABLE else None)

            if (
                    combined_integration.message != event["text"]
                    or combined_integration.attachments
            ):
                if token is not UNABLE:
                    resp = requests.post(
                        "https://slack.com/api/chat.update",
                        json={
                            "channel": event["channel"],
                            "ts": event["ts"],
                            "as_user": True,
                            "text": combined_integration.message,
                            "attachments": combined_integration.attachments,
                        },
                        headers={"Authorization": "Bearer {}".format(token)},
                    ).json()
                    if not resp["ok"] and resp["error"] in {
                        "invalid_auth",
                        "token_revoked",
                        "account_inactive",
                        "missing_scope",
                    }:
                        # token available, but no permissions
                        token = UNABLE

                if token is UNABLE:
                    requests.post(
                        "https://slack.com/api/chat.postEphemeral",
                        json={
                            "blocks": make_promo_block(combined_integration.message),
                            "attachments": [],
                            "channel": event["channel"],
                            "user": event["user"],
                        },
                        headers={"Authorization": "Bearer {}".format(ACCESS_TOKEN_61A)},
                    ).json()

        except Exception as e:
            print("".join(traceback.TracebackException.from_exception(e).format()))
        finally:
            if "challenge" in d:
                return d["challenge"]
            return ""
