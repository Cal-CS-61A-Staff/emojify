from functools import wraps


def slack_signed(route):
    @wraps(route)
    def wrapped(*args, **kwargs):
        return route(*args, **kwargs)
    return wrapped
