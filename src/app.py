import traceback

from sqlalchemy import create_engine, text
import os.path
import requests
from flask import Flask, request, jsonify, redirect

from emoji_integration import EmojiIntegration
from integration import combine_integrations
from piazza_integration import PiazzaIntegration

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")

CLIENT_SECRET = os.getenv("CLIENT_SECRET")

SIGNING_SECRET = os.getenv("SIGNING_SECRET")

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


@app.route("/")
def index():
    return redirect(
        f"https://slack.com/oauth/authorize?client_id={CLIENT_ID}&scope=channels:history,channels:write,chat:write:user,users:read,groups:history,im:history,mpim:history"
    )


@app.route("/oauth")
def oauth():
    if not request.args["code"]:
        return jsonify({"Error": "sadcat"}), 500
    resp = requests.post(
        "https://slack.com/api/oauth.access",
        {
            "code": request.args["code"],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    if resp.status_code == 200:
        store_user_token(resp.json()["user_id"], resp.json()["access_token"])
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
        out = conn.execute("SELECT token FROM tokens WHERE user=%s", (user,)).first()[
            "token"
        ]
    return out


@app.route("/interactive_handler", methods=["POST"])
def handler():
    return ""


@app.route("/message_send", methods=["POST"])
def message_send():
    d = request.json
    try:
        if "challenge" in d:
            return
        event = d["event"]
        token = get_user_token(event["user"])
        if "edited" in event:
            return
        if "subtype" in event:
            return

        combined_integration = combine_integrations([EmojiIntegration, PiazzaIntegration])(event["text"], token)

        requests.post(
            "https://slack.com/api/chat.update",
            json={
                "channel": event["channel"],
                "ts": event["ts"],
                "as_user": True,
                "text": combined_integration.text,
                "attachments": combined_integration.attachments
            },
            headers={"Authorization": "Bearer {}".format(token)},
        )

    except Exception as e:
        print("".join(traceback.TracebackException.from_exception(e).format()))
    finally:
        if "challenge" in d:
            return d["challenge"]
        return ""


if __name__ == "__main__":
    app.run()
