from flask import Flask

from config_client import create_config_client
from slack_client import create_slack_client

from oauth_client import create_oauth_client

app = Flask(__name__)

if __name__ == '__main__':
    app.debug = True

create_config_client(app)
create_slack_client(app)
create_oauth_client(app)

if __name__ == "__main__":
    app.run(debug=True)
