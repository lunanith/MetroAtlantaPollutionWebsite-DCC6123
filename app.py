from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import os

load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

SENDER_EMAIL    = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")


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


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True)