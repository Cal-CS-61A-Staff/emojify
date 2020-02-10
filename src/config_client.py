import json

from flask import request, url_for, abort
from werkzeug.utils import redirect

from auth import query
from db import connect_db
from env import CLIENT_ID
from security import logged_in, get_staff_endpoints

REJECTED = object()
UNABLE = object()

ADD_TO_SLACK = f"https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&scope=channels:join,channels:read,chat:write&user_scope=channels:history,chat:write,groups:history,im:history,mpim:history,users:read"

with open("config.json") as f:
    CONFIG = json.load(f)


def init_db():
    with connect_db() as db:
        db(
            """CREATE TABLE IF NOT EXISTS tokens (
        user varchar(128),
        token text,
        PRIMARY KEY (`user`)
    );"""
        )

        db(
            """CREATE TABLE IF NOT EXISTS silenced_users (
                user varchar(128),            
                PRIMARY KEY (`user`)       
            );"""
        )

        db(
            """CREATE TABLE IF NOT EXISTS bot_data (
                bot_access_token varchar(256),
                auth_client varchar(128),
                auth_secret varchar(256),
                team_id varchar(256),
                course varchar(128)
            )"""
        )

        db(
            """CREATE TABLE IF NOT EXISTS activated_services (
                course varchar(128),
                service varchar(128)
            )"""
        )


init_db()


def get_endpoint(course):
    return query("/api/{}/get_endpoint".format(course), course=None)


def create_config_client(app):
    @app.route("/")
    @logged_in
    def index():
        staff_endpoints = set(get_staff_endpoints(app.remote))
        active_courses = []
        for course in CONFIG:
            if get_endpoint(course) in staff_endpoints:
                active_courses.append(course)

        if len(active_courses) == 0:
            return (
                "You are not a member of staff in any course that uses this tool",
                401,
            )
        if len(active_courses) == 1:
            return redirect(url_for("register_course", course=active_courses[0]))

        options = "<p>".join(
            '<button formaction="register/{}">{}</button>'.format(course, course)
            for course in active_courses
        )

        return f"""
            Please select your course:
            <form method="get">
                {options}
            </form>
        """

    @app.route("/register/<course>")
    def register_course(course):
        print(get_endpoint(course), list(get_staff_endpoints(app.remote)))
        if get_endpoint(course) not in get_staff_endpoints(app.remote):
            abort(403)

        with connect_db() as db:
            ret = db("SELECT * FROM bot_data WHERE course = (%s)", [course]).fetchone()

        if ret:
            # course already setup
            return redirect(ADD_TO_SLACK)
        else:
            return redirect(url_for("course_config", course=course))

    @app.route("/config/<course>")
    def course_config(course):
        if get_endpoint(course) not in get_staff_endpoints(app.remote):
            abort(403)

        with connect_db() as db:
            ret = db(
                "SELECT auth_client FROM bot_data WHERE course = (%s)", [course]
            ).fetchone()

        client = ret[0] if ret else ""

        return f"""
            First, ensure that <a href="https://auth.apps.cs61a.org">61A Auth</a> is set up for your course.
            <p>
            Create a client on 61A Auth with staff access to Piazza. Then, set up the slackbot:
            <form action="{url_for("set_course_config", course=course)}" method="post">
                <label>
                    Client name: <br />
                    <input name="client_name" type="text" placeholder="{client}"> <br />
                </label>
                <label>
                    Client secret: <br />
                    <input name="client_secret" type="text" placeholder="HIDDEN"> <br />
                </label>
                 <br />
                <input type="submit" />
            </form>
            <p>
            Then, <a href="{ADD_TO_SLACK}">add the slackbot to your workspace!</a>
        """

    @app.route("/set_config/<course>", methods=["POST"])
    def set_course_config(course):
        if get_endpoint(course) not in get_staff_endpoints(app.remote):
            abort(403)

        client_name = request.form["client_name"]
        client_secret = request.form["client_secret"]

        with connect_db() as db:
            check = db(
                "SELECT * FROM bot_data WHERE course = (%s)", [course]
            ).fetchone()
            if not check:
                db(
                    "INSERT INTO bot_data VALUES (%s, %s, %s, %s, %s)",
                    ["", client_name, client_secret, "", course],
                )
            else:
                db(
                    "UPDATE bot_data SET auth_client=(%s), auth_secret=(%s) WHERE course=(%s)",
                    [client_name, client_secret, course],
                )

        return redirect(url_for("course_config", course=course))


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


def store_bot_token(course, team_id, token):
    with connect_db() as db:
        db("UPDATE bot_data SET bot_access_token=(%s), team_id=(%s) WHERE course=(%s)", [token, team_id, course])


def get_team_data(team_id):
    with connect_db() as db:
        return db("SELECT course, bot_access_token FROM bot_data WHERE team_id = (%s)", [team_id]).fetchone()
