from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import os
import hmac
import json
import uuid
import secrets
from datetime import datetime

load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")
# Secret key for signing session cookies. In production set FLASK_SECRET_KEY in .env;
# falls back to a random per-process key for dev (sessions reset on restart).
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
CORS(app, supports_credentials=True)

SENDER_EMAIL    = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# Admin password — set ADMIN_PASSWORD in .env. The default is for local dev only.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


def admin_required(f):
    """Decorator that returns 401 if the request isn't from a logged-in admin."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"success": False, "error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return wrapper

# --- Bug report storage configuration ---
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
DATA_DIR          = os.path.join(BASE_DIR, "data")
BUG_REPORTS_FILE  = os.path.join(DATA_DIR, "bug_reports.json")
SCREENSHOTS_DIR   = os.path.join(BASE_DIR, "public", "uploads", "bug_screenshots")
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_SCREENSHOT_MB = 5
ALLOWED_SEVERITY  = {"low", "medium", "high", "critical"}

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def _load_bug_reports():
    if not os.path.exists(BUG_REPORTS_FILE):
        return []
    try:
        with open(BUG_REPORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_bug_reports(reports):
    with open(BUG_REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)


def _allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT
    )


def is_valid_email(email):
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return re.match(pattern, email) is not None


@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json()

    name    = (data.get("name")    or "").strip()
    email   = (data.get("email")   or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    errors = {}
    if not name:
        errors["name"] = "Name is required."
    if not email or not is_valid_email(email):
        errors["email"] = "A valid email address is required."
    if not subject:
        errors["subject"] = "Subject is required."
    if not message:
        errors["message"] = "Message is required."

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"MAP-USA Contact Form: {subject}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg["Reply-To"] = email

    body = f"""
You have received a new message via the MAP-USA contact form.

Name:    {name}
Email:   {email}
Subject: {subject}

Message:
{message}
    """.strip()

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    except Exception as e:
        print(f"Email sending failed: {e}")
        return jsonify({"success": False, "error": "Failed to send email. Please try again later."}), 500

    return jsonify({"success": True, "message": "Your message has been sent!"}), 200


@app.route("/api/report-bug", methods=["POST"])
def report_bug():
    """Accepts a bug report (multipart/form-data) with optional screenshot."""
    title       = (request.form.get("title")       or "").strip()
    description = (request.form.get("description") or "").strip()
    severity    = (request.form.get("severity")    or "").strip().lower()

    errors = {}
    if not title:
        errors["title"] = "Issue title is required."
    elif len(title) > 200:
        errors["title"] = "Title must be 200 characters or fewer."

    if not description:
        errors["description"] = "Description is required."
    elif len(description) > 5000:
        errors["description"] = "Description must be 5000 characters or fewer."

    if severity not in ALLOWED_SEVERITY:
        errors["severity"] = "Severity must be one of: low, medium, high, critical."

    # Optional screenshot
    screenshot_url = None
    screenshot_file = request.files.get("screenshot")
    if screenshot_file and screenshot_file.filename:
        if not _allowed_image(screenshot_file.filename):
            errors["screenshot"] = "Screenshot must be PNG, JPG, JPEG, GIF, or WEBP."
        else:
            screenshot_file.seek(0, os.SEEK_END)
            size_mb = screenshot_file.tell() / (1024 * 1024)
            screenshot_file.seek(0)
            if size_mb > MAX_SCREENSHOT_MB:
                errors["screenshot"] = f"Screenshot must be under {MAX_SCREENSHOT_MB} MB."

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    report_id = uuid.uuid4().hex[:12]

    if screenshot_file and screenshot_file.filename and "screenshot" not in errors:
        ext = screenshot_file.filename.rsplit(".", 1)[1].lower()
        safe_name = secure_filename(f"{report_id}.{ext}")
        save_path = os.path.join(SCREENSHOTS_DIR, safe_name)
        screenshot_file.save(save_path)
        # URL relative to static_folder ("public")
        screenshot_url = f"/uploads/bug_screenshots/{safe_name}"

    report = {
        "id": report_id,
        "title": title,
        "description": description,
        "severity": severity,
        "screenshot_url": screenshot_url,
        "status": "open",
        "submitted_at": datetime.utcnow().isoformat() + "Z",
    }

    reports = _load_bug_reports()
    reports.append(report)
    _save_bug_reports(reports)

    # Best-effort admin email notification (won't fail the request if email is down)
    if SENDER_EMAIL and SENDER_PASSWORD and RECIPIENT_EMAIL:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[MAP-USA Bug Report - {severity.upper()}] {title}"
            msg["From"]    = SENDER_EMAIL
            msg["To"]      = RECIPIENT_EMAIL

            body = f"""
A new bug report has been submitted on MAP-USA.

Report ID:  {report_id}
Severity:   {severity}
Title:      {title}
Submitted:  {report['submitted_at']}

Description:
{description}

Screenshot: {screenshot_url or '(none)'}

View all reports on the admin page.
            """.strip()
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        except Exception as e:
            print(f"Bug report email notification failed: {e}")

    return jsonify({
        "success": True,
        "message": "Thanks! Your bug report has been submitted.",
        "report_id": report_id,
    }), 201


@app.route("/api/bug-reports", methods=["GET"])
@admin_required
def list_bug_reports():
    """Returns all bug reports for the admin page (newest first)."""
    reports = _load_bug_reports()
    reports_sorted = sorted(reports, key=lambda r: r.get("submitted_at", ""), reverse=True)
    return jsonify({"success": True, "reports": reports_sorted}), 200


@app.route("/api/bug-reports/<report_id>", methods=["PATCH"])
@admin_required
def update_bug_report(report_id):
    """Update a bug report's status (e.g., mark as resolved)."""
    data = request.get_json() or {}
    new_status = (data.get("status") or "").strip().lower()

    if new_status not in {"open", "in_progress", "resolved"}:
        return jsonify({
            "success": False,
            "error": "Status must be one of: open, in_progress, resolved.",
        }), 400

    reports = _load_bug_reports()
    found = None
    for r in reports:
        if r.get("id") == report_id:
            r["status"] = new_status
            found = r
            break

    if not found:
        return jsonify({"success": False, "error": "Report not found."}), 404

    _save_bug_reports(reports)
    return jsonify({"success": True, "report": found}), 200


@app.route("/api/bug-reports/<report_id>", methods=["DELETE"])
@admin_required
def delete_bug_report(report_id):
    """Delete a bug report (and its screenshot, if any)."""
    reports = _load_bug_reports()
    remaining = [r for r in reports if r.get("id") != report_id]
    if len(remaining) == len(reports):
        return jsonify({"success": False, "error": "Report not found."}), 404

    # Best-effort screenshot cleanup
    deleted = next((r for r in reports if r.get("id") == report_id), None)
    if deleted and deleted.get("screenshot_url"):
        fname = os.path.basename(deleted["screenshot_url"])
        fpath = os.path.join(SCREENSHOTS_DIR, fname)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except OSError:
                pass

    _save_bug_reports(remaining)
    return jsonify({"success": True}), 200


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    password = data.get("password") or ""
    # Constant-time comparison to avoid timing attacks
    if hmac.compare_digest(password, ADMIN_PASSWORD):
        session["is_admin"] = True
        session.permanent = False
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Incorrect password."}), 401


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True}), 200


@app.route("/api/admin/status", methods=["GET"])
def admin_status():
    return jsonify({"authenticated": bool(session.get("is_admin"))}), 200


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True)