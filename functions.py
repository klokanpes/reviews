
from functools import wraps
from flask import redirect, render_template, session

# adapted from cs50's finance problem set
def apology(message):
    """
    Error message for the user
    """

    return render_template("apology.html", message=message)


# used from CS50's finance problem set.
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function