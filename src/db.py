import os
from contextlib import contextmanager

# noinspection PyUnresolvedReferences
from time import sleep

import __main__
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

NUM_RETRIES = 5
SLEEP_DELAY = 2

if __main__.__file__.endswith("app.py"):
    engine = create_engine("mysql://localhost/emojify")
else:
    engine = create_engine(os.getenv("DATABASE_URL"))


@contextmanager
def connect_db():
    def db(*args):
        for _ in range(NUM_RETRIES):
            with engine.connect() as conn:
                try:
                    try:
                        if isinstance(args[1][0], str):
                            raise TypeError
                    except (IndexError, TypeError):
                        return conn.execute(*args)
                    else:
                        for data in args[1]:
                            conn.execute(args[0], data, *args[2:])
                except OperationalError as e:
                    print("MySQL Failure, retrying in {} seconds...".format(SLEEP_DELAY), e)
                    sleep(SLEEP_DELAY)
                    continue
                else:
                    break
        else:
            print("{} repeated failures, transaction failed".format(NUM_RETRIES))

    yield db
