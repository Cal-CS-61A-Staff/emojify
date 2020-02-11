import hashlib
import hmac
import time
from functools import wraps

from flask import session, request, current_app, url_for, redirect, abort

from env import SIGNING_SECRET

AUTHORIZED_ROLES = ["staff", "instructor", "grader"]


def slack_signed(route):
    @wraps(route)
    def wrapped(*args, **kwargs):
        data = request.get_data().decode("utf-8")
        timestamp = request.headers["X-Slack-Request-Timestamp"]
        slack_signature = request.headers['X-Slack-Signature']
        if abs(time.time() - int(timestamp)) > 60 * 5:
            abort(403)
        basestring = "v0:" + timestamp + ":" + data
        my_signature = "v0=" + hmac.new(SIGNING_SECRET.encode(), basestring.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(my_signature.encode(), slack_signature.encode()):
            return route(*args, **kwargs)
        else:
            abort(403)
    return wrapped


def get_staff_endpoints(remote):
    try:
        token = session.get("dev_token") or request.cookies.get("dev_token")
        if not token:
            return False
        ret = remote.get("user")
        for course in ret.data["data"]["participations"]:
            if course["role"] not in AUTHORIZED_ROLES:
                continue
            yield course["course"]["offering"]
    except Exception as e:
        # fail safe!
        print(e)
        return False


def logged_in(route):
    @wraps(route)
    def wrapped(*args, **kwargs):
        if not list(get_staff_endpoints(current_app.remote)):
            return redirect(url_for("login"))
        return route(*args, **kwargs)
    return wrapped
