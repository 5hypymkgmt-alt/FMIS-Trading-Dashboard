import os
import hmac
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, abort, redirect, render_template_string,
    request, send_from_directory, session, url_for
)
from werkzeug.security import check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get(
        "FMIS_SECURE_COOKIES", ""
    ).lower() == "true",
    MAX_CONTENT_LENGTH=16 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

USERNAME = os.environ.get("FMIS_USERNAME", "")
PASSWORD_HASH = os.environ.get("FMIS_PASSWORD_HASH", "")

if not all((
    app.config["SECRET_KEY"],
    USERNAME,
    PASSWORD_HASH
)):
    raise RuntimeError("FMIS authentication settings missing")

LOGIN_PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
 content="width=device-width,initial-scale=1">
<title>FMIS Private Login</title>
<style>
body {
  background:#0b1220;
  color:#e8edf5;
  font-family:Arial,sans-serif;
  display:grid;
  place-items:center;
  min-height:100vh;
  margin:0;
}
form {
  background:#172235;
  padding:32px;
  border-radius:12px;
  width:min(320px,85vw);
}
input,button {
  box-sizing:border-box;
  width:100%;
  padding:12px;
  margin:9px 0;
  border-radius:6px;
}
button {
  background:#29dc78;
  border:0;
  cursor:pointer;
  font-weight:bold;
}
.error {color:#ff6677}
</style>
</head>
<body>
<form method="post">
<h2>FMIS Trading Dashboard</h2>
<p>Private Access</p>
<input name="username" placeholder="Username"
 autocomplete="username" required>
<input name="password" type="password"
 placeholder="Password"
 autocomplete="current-password" required>
<button type="submit">Sign In</button>
{% if error %}
<p class="error">Invalid username or password</p>
{% endif %}
</form>
</body>
</html>
"""

@app.after_request
def security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )
    return response

@app.route("/health")
def health():
    return {"status": "ok"}

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
)

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        valid_user = hmac.compare_digest(
            username.encode(), USERNAME.encode()
        )
        valid_password = check_password_hash(
            PASSWORD_HASH, password
        )

        if valid_user and valid_password:
            session.clear()
            session.permanent = True
            session["authenticated"] = True
            return redirect(url_for("dashboard"))

        return render_template_string(
            LOGIN_PAGE, error=True
        ), 401

    return render_template_string(
        LOGIN_PAGE, error=False
    )

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

PROTECTED_FILES = {
    "index.html",
    "data.json",
    "calendar-data.json",
    "fmis-gold-intelligence.js",
    "fmis-calendar.js",
    "fmis-energy-ribbons.svg",
    "calendar-api-test.html",
}

@app.route("/")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:filename>")
def protected_file(filename):
    if not session.get("authenticated"):
        return redirect(url_for("login"))

    if filename not in PROTECTED_FILES:
        abort(404)

    return send_from_directory(BASE_DIR, filename)

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
