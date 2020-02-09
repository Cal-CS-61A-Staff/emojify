import json
import traceback

from sqlalchemy import create_engine, text
import os.path
import requests
from flask import Flask, request, jsonify, redirect

from emoji_integration import EmojiIntegration
from golink_integration import GoLinkIntegration
from integration import combine_integrations
from piazza_integration import PiazzaIntegration
from promotions import make_promo_block
from security import slack_signed

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")

CLIENT_SECRET = os.getenv("CLIENT_SECRET")

ACCESS_TOKEN_61A = os.getenv("ACCESS_TOKEN_61A")

REJECTED = object()
UNABLE = object()

if os.getenv("FLASK_ENV") == "development":
    engine = create_engine("mysql://localhost/emojify")
else:
    engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    statement = text(
        """CREATE TABLE IF NOT EXISTS tokens (
    user varchar(128),
    token text,
    PRIMARY KEY (`user`)
);"""
    )
    conn.execute(statement)

    statement = text(
        """CREATE TABLE IF NOT EXISTS silenced_users (
            user varchar(128),            
            PRIMARY KEY (`user`)       
        );"""
    )

    conn.execute(statement)


@app.route("/")
def index():
    return redirect(
        f"https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&scope=chat:write&user_scope=channels:history,groups:history,im:history,mpim:history,chat:write"
    )


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


def store_user_token(user, token):
    with engine.connect() as conn:
        result = conn.execute("SELECT user FROM tokens WHERE user=%s", (user,))
        if not result.first():
            conn.execute("INSERT INTO tokens VALUES (%s, %s)", (user, token))
        conn.execute("UPDATE tokens SET token=(%s) WHERE user=(%s)", (token, user))


def get_user_token(user):
    with engine.connect() as conn:
        out = conn.execute("SELECT token FROM tokens WHERE user=%s", (user,)).first()
        if not out:
            check = conn.execute(
                "SELECT user FROM silenced_users WHERE user=%s", (user,)
            ).first()
            if check:  # user doesn't want to use the tool :(
                return REJECTED
            return UNABLE
        return out["token"]


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
        with engine.connect() as conn:
            conn.execute("INSERT INTO silenced_users VALUES (%s)", (user_id,))
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


if __name__ == "__main__":
    app.run()
