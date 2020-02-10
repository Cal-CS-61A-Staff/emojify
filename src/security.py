from functools import wraps

from flask import session, request, current_app, url_for, redirect

AUTHORIZED_ROLES = ["staff", "instructor", "grader"]


def slack_signed(route):
    @wraps(route)
    def wrapped(*args, **kwargs):
        return route(*args, **kwargs)
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
