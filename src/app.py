import random
import traceback
from html import unescape

from sqlalchemy import create_engine, text
import re
import os.path
import requests
from flask import Flask, request, jsonify, redirect
from string import punctuation

from staff import STAFF, STAFF_EMOJI

app = Flask(__name__)

PORT = 4390

CLIENT_ID = "889493798706.908148713520"

CLIENT_SECRET = "ebcb324338a27e02f9b40d3a9cfd1be0"

SIGNING_SECRET = "ee5339f5f06e4b9bf2fc6413f45a51c1"

CLIENT_NAME = "emojify"
AUTH_KEY = "RRQH1SSHXGUU676S3RDRNFCT0TJJUXN4WKER0YQ5DN8M53PE59TJLGTW8HYXYM4V"

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

cached_names = {}


@app.route("/")
def hello_world():
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


@app.route("/ping", methods=["POST"])
def ping():
    return "woot"


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


def get_name(id, token):
    if id in cached_names:
        return cached_names[id]
    resp = requests.post(
        "https://slack.com/api/users.info", {"token": token, "user": id}
    )
    out = resp.json()["user"]["real_name"]
    cached_names[id] = out
    return out


def get_staff(word, token):
    candidates = set()
    if word.startswith("<@") and word.endswith(">"):
        word = get_name(word[2:-1], token)
    for staff in STAFF:
        if (staff.firstName + " " + staff.lastName).lower() == word.lower():
            candidates.add(staff)
    for staff in STAFF:
        if word.lower() == (staff.firstName + " " + staff.lastName[0]).lower():
            candidates.add(staff)
    for staff in STAFF:
        if staff.firstName.lower() == word.lower():
            candidates.add(staff)
    if candidates:
        return random.choice(list(candidates))


def strip_punctuation(word):
    if word.startswith("<@") and word.endswith(">"):
        return "", word, ""
    rest = word.lstrip(punctuation)
    leading = word[: len(word) - len(rest)]
    stripped = rest.rstrip(punctuation)
    trailing = rest[len(stripped) :]
    print(word, leading, stripped, trailing)
    return leading, stripped, trailing


def has_staff_emoji(text):
    emojis = re.findall(":.+?:", text)
    for emoji in emojis:
        if emoji in STAFF_EMOJI:
            return True
    return False


def process(text, token):
    text.replace("<@", " <@")
    text.replace("  <@", " <@")
    if text.startswith(" <@"):
        text = text[1:]
    words = text.split(" ")

    if has_staff_emoji(text):
        return text

    for i, word in enumerate(words):
        if not words[i]:
            continue

        if i != len(words) - 1:
            next_word = words[i + 1]
            combined = word + " " + next_word
            leading, stripped, trailing = strip_punctuation(combined)
            staff = get_staff(stripped, token)
            if staff is not None:
                words[i] = leading + combined + f" ({staff.emoji}) " + trailing
                words[i + 1] = ""
                continue

        leading, stripped, trailing = strip_punctuation(word)
        staff = get_staff(stripped, token)
        if staff is None:
            continue
        words[i] = leading + stripped + f" ({staff.emoji})" + trailing
    return " ".join(words)


@app.route("/interactive_handler", methods=["POST"])
def handler():
    return ""


@app.route("/message_send", methods=["POST"])
def message_send():
    # TODO: VERIFY SIGNING TOKEN!!!
    fail = False
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

        processed = process(event["text"], token)

        match = re.search("@([0-9]+)", processed)
        if match:
            cid = int(match.group(1))
            print("HANDLING: {}".format(cid))
            resp = requests.post("https://auth.apps.cs61a.org/piazza/get_post", json={
                "staff": True,
                "cid": cid,
                "client_name": CLIENT_NAME,
                "secret": AUTH_KEY,
            }).json()
            subject = resp["history"][0]["subject"]
            content = resp["history"][0]["content"]

            content = unescape(re.sub('<[^<]+?>', '', content))

            print(
                requests.post(
                    "https://slack.com/api/chat.update",
                    json={
                        "channel": event["channel"],
                        "ts": event["ts"],
                        "as_user": True,
                        "blocks": [
                            {
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": processed},
                            },
                            {"type": "divider"},
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":piazza: *{}* \n {}".format(subject, content),
                                },
                                "accessory": {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Open"},
                                    "value": "piazza_open_click",
                                    "url": "https://piazza.com/class/k5g56y7yegw5xr?cid={}".format(cid)
                                },
                            },
                            {
                                "type": "context",
                                "elements": [
                                    {
                                        "type": "mrkdwn",
                                        "text": "Piazza integration provided by emojify.apps.cs61a.org",
                                    }
                                ],
                            },
                        ],
                    },
                    headers={"Authorization": "Bearer {}".format(token)},
                ).json()
            )
        elif event["text"] != processed:
            requests.post(
                "https://slack.com/api/chat.update",
                {
                    "token": token,
                    "channel": event["channel"],
                    "text": processed,
                    "ts": event["ts"],
                    "as_user": True,
                },
            )

    except Exception as e:
        fail = True
        print("".join(traceback.TracebackException.from_exception(e).format()))
    finally:
        if "challenge" in d:
            return d["challenge"]
        return ""


if __name__ == "__main__":
    app.run(port=PORT)
