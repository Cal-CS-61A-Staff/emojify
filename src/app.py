from flask import Flask

from config import create_config_client
from db import connect_db
from slack import create_slack_client

app = Flask(__name__)

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
            course varchar(128)
        )"""
    )


create_config_client(app)
create_slack_client(app)

if __name__ == "__main__":
    app.run()
