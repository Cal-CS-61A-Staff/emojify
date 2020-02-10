from werkzeug.utils import redirect

from db import connect_db
from env import CLIENT_ID

REJECTED = object()
UNABLE = object()


def create_config_client(app):
    @app.route("/")
    def index():
        return redirect(
            f"https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&scope=channels:join,channels:read,chat:write&user_scope=channels:history,chat:write,groups:history,im:history,mpim:history,users:read"
        )


def store_user_token(user, token):
    with connect_db() as db:
        result = db("SELECT user FROM tokens WHERE user=%s", (user,))
        if not result.fetchone():
            db("INSERT INTO tokens VALUES (%s, %s)", (user, token))
        db("UPDATE tokens SET token=(%s) WHERE user=(%s)", (token, user))


def get_user_token(user):
    with connect_db() as db:
        out = db("SELECT token FROM tokens WHERE user=%s", (user,)).fetchone()
        if not out:
            check = db(
                "SELECT user FROM silenced_users WHERE user=%s", (user,)
            ).fetchone()
            if check:  # user doesn't want to use the tool :(
                return REJECTED
            return UNABLE
        return out["token"]
