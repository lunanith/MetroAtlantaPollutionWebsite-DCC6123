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
import glob
import csv
import secrets
from datetime import datetime, timezone
from urllib import error as urllib_error
from urllib import request as urllib_request
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()


FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
if FIREBASE_CREDENTIALS_PATH:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    USE_FIREBASE = True
else:
    USE_FIREBASE = False

app = Flask(__name__, static_folder="public", static_url_path="")

app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
CORS(app, supports_credentials=True)

SENDER_EMAIL    = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Admin password — set ADMIN_PASSWORD in .env. The default is for local dev only.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
CHAT_HISTORY_SESSION_KEY = "chat_history"
MAX_CHAT_HISTORY_MESSAGES = 10
CHATBOT_SYSTEM_PROMPT = """
You are the MAP-USA AI assistant for a Metro Atlanta air pollution website.
Help users understand air pollution concepts, pollution maps, trends, research projects,
and the educational content on the site. Be clear, concise, and friendly.
If a question goes beyond the site topics, still try to help, but say when you are not certain.
Do not claim to have live data unless the user explicitly provides it in the conversation.
Keep answers short and readable for students, educators, and community members.
Use the provided sensor dataset context when a user asks about measurements, trends, dates,
AQI, PM values, temperature, humidity, pressure, gas, or other sensor readings.
""".strip()


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
SENSOR_DATA_DIR   = os.path.join(BASE_DIR, "public", "data")
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_SCREENSHOT_MB = 5
ALLOWED_SEVERITY  = {"low", "medium", "high", "critical"}
MAX_SENSOR_CONTEXT_CHARS = 18000
DEFAULT_SENSOR_COLUMNS = [
    "pm2_5_atm",
    "pm10_0_atm",
    "pm1_0_atm",
    "pm2.5_aqi_atm",
    "current_temp_f",
    "current_humidity",
    "pressure",
    "gas",
]
SENSOR_COLUMN_KEYWORDS = {
    "pm1": ["pm1_0_atm", "pm1_0_cf_1", "pm1_0_atm_b", "pm1_0_cf_1_b"],
    "pm2.5": ["pm2_5_atm", "pm2_5_cf_1", "pm2_5_atm_b", "pm2_5_cf_1_b", "pm2.5_aqi_atm", "pm2.5_aqi_cf_1"],
    "pm25": ["pm2_5_atm", "pm2_5_cf_1", "pm2_5_atm_b", "pm2_5_cf_1_b", "pm2.5_aqi_atm", "pm2.5_aqi_cf_1"],
    "aqi": ["pm2.5_aqi_atm", "pm2.5_aqi_cf_1", "pm2.5_aqi_atm_b", "pm2.5_aqi_cf_1_b"],
    "pm10": ["pm10_0_atm", "pm10_0_cf_1", "pm10_0_atm_b", "pm10_0_cf_1_b"],
    "temperature": ["current_temp_f", "current_dewpoint_f"],
    "temp": ["current_temp_f", "current_dewpoint_f"],
    "humidity": ["current_humidity"],
    "dewpoint": ["current_dewpoint_f"],
    "pressure": ["pressure"],
    "gas": ["gas"],
    "particle": ["p_0_3_um", "p_0_5_um", "p_1_0_um", "p_2_5_um", "p_5_0_um", "p_10_0_um"],
    "particles": ["p_0_3_um", "p_0_5_um", "p_1_0_um", "p_2_5_um", "p_5_0_um", "p_10_0_um"],
}
MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def _load_bug_reports():
    if not USE_FIREBASE:
        if not os.path.exists(BUG_REPORTS_FILE):
            return []
        try:
            with open(BUG_REPORTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    
    try:
        reports_ref = db.collection('bug_reports')
        docs = reports_ref.order_by('submitted_at', direction=firestore.Query.DESCENDING).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Firebase error: {e}")
        return []


def _save_bug_reports(reports):
    if not USE_FIREBASE:
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


def _safe_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_stat_value(value):
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _parse_sensor_timestamp(value):
    try:
        return datetime.strptime(value, "%Y/%m/%dT%H:%M:%Sz")
    except ValueError:
        return None


def _extract_dates_from_message(message):
    dates = set()

    for match in re.findall(r"\b(20\d{2})[-/](\d{2})[-/](\d{2})\b", message):
        year, month, day = map(int, match)
        dates.add(f"{year:04d}-{month:02d}-{day:02d}")

    for match in re.findall(r"\b(20\d{2})(\d{2})(\d{2})\b", message):
        year, month, day = map(int, match)
        dates.add(f"{year:04d}-{month:02d}-{day:02d}")

    month_pattern = re.compile(
        r"\b(" + "|".join(MONTH_NAME_TO_NUMBER.keys()) + r")\s+(\d{1,2})(?:,\s*(20\d{2}))?\b",
        re.IGNORECASE,
    )
    for month_name, day_text, year_text in month_pattern.findall(message):
        year = int(year_text) if year_text else 2025
        month = MONTH_NAME_TO_NUMBER[month_name.lower()]
        day = int(day_text)
        dates.add(f"{year:04d}-{month:02d}-{day:02d}")

    return sorted(dates)


def _pick_sensor_columns(message):
    lowered = message.lower()
    chosen = []
    for keyword, columns in SENSOR_COLUMN_KEYWORDS.items():
        if keyword in lowered:
            for column in columns:
                if column not in chosen:
                    chosen.append(column)

    if not chosen:
        return DEFAULT_SENSOR_COLUMNS[:]

    for fallback in DEFAULT_SENSOR_COLUMNS:
        if fallback not in chosen and len(chosen) < 8:
            chosen.append(fallback)
    return chosen[:8]


def _row_matches_question(row, message):
    lowered = message.lower()

    if "highest" in lowered or "peak" in lowered or "max" in lowered:
        return True
    if "lowest" in lowered or "minimum" in lowered or "min" in lowered:
        return True
    if any(word in lowered for word in ["temperature", "temp", "humidity", "pressure", "gas", "aqi", "pm"]):
        return True

    return False


def _summarize_sensor_file(sensor_file, selected_columns):
    summary_bits = [
        f"date={sensor_file['date']}",
        f"rows={sensor_file['row_count']}",
        f"sensor={sensor_file['mac_address'] or 'unknown'}",
    ]

    for column in selected_columns[:4]:
        stats = sensor_file["stats"].get(column)
        if not stats or stats["count"] == 0:
            continue
        avg = stats["sum"] / stats["count"]
        summary_bits.append(
            f"{column}: avg={_format_stat_value(avg)} min={_format_stat_value(stats['min'])} max={_format_stat_value(stats['max'])}"
        )

    return "; ".join(summary_bits)


def _load_sensor_data():
    dataset = {
        "files": [],
        "by_date": {},
        "file_count": 0,
        "row_count": 0,
        "available_dates": [],
        "date_range": None,
        "all_columns": [],
        "sensor_ids": set(),
        "global_stats": {},
    }

    for path in sorted(glob.glob(os.path.join(SENSOR_DATA_DIR, "*.csv"))):
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            file_stats = {}
            columns = reader.fieldnames or []
            for row in reader:
                timestamp = _parse_sensor_timestamp(row.get("UTCDateTime", ""))
                if not timestamp:
                    continue
                row["parsed_timestamp"] = timestamp
                row["date_key"] = timestamp.strftime("%Y-%m-%d")
                rows.append(row)

                for column in columns:
                    numeric_value = _safe_float(row.get(column))
                    if numeric_value is None:
                        continue
                    stat = file_stats.setdefault(column, {"count": 0, "sum": 0.0, "min": numeric_value, "max": numeric_value})
                    stat["count"] += 1
                    stat["sum"] += numeric_value
                    stat["min"] = min(stat["min"], numeric_value)
                    stat["max"] = max(stat["max"], numeric_value)

                    global_stat = dataset["global_stats"].setdefault(
                        column,
                        {"count": 0, "sum": 0.0, "min": numeric_value, "max": numeric_value},
                    )
                    global_stat["count"] += 1
                    global_stat["sum"] += numeric_value
                    global_stat["min"] = min(global_stat["min"], numeric_value)
                    global_stat["max"] = max(global_stat["max"], numeric_value)

            if not rows:
                continue

            rows.sort(key=lambda item: item["parsed_timestamp"])
            date_key = rows[0]["date_key"]
            sensor_file = {
                "path": path,
                "filename": os.path.basename(path),
                "date": date_key,
                "rows": rows,
                "row_count": len(rows),
                "stats": file_stats,
                "columns": columns,
                "mac_address": rows[0].get("mac_address", ""),
            }
            dataset["files"].append(sensor_file)
            dataset["by_date"][date_key] = sensor_file
            dataset["row_count"] += len(rows)
            dataset["sensor_ids"].add(sensor_file["mac_address"])
            if not dataset["all_columns"]:
                dataset["all_columns"] = columns

    dataset["file_count"] = len(dataset["files"])
    dataset["available_dates"] = [sensor_file["date"] for sensor_file in dataset["files"]]
    if dataset["available_dates"]:
        dataset["date_range"] = (dataset["available_dates"][0], dataset["available_dates"][-1])
    return dataset


SENSOR_DATASET = _load_sensor_data()


def _build_sensor_dataset_context(message):
    if not SENSOR_DATASET["files"]:
        return "No sensor dataset is currently loaded."

    selected_columns = _pick_sensor_columns(message)
    requested_dates = _extract_dates_from_message(message)
    lowered = message.lower()

    if requested_dates:
        chosen_files = [SENSOR_DATASET["by_date"][date] for date in requested_dates if date in SENSOR_DATASET["by_date"]]
    elif any(term in lowered for term in ["latest", "recent", "newest", "today", "current"]):
        chosen_files = SENSOR_DATASET["files"][-3:]
    else:
        chosen_files = SENSOR_DATASET["files"][-5:]

    if not chosen_files:
        chosen_files = SENSOR_DATASET["files"][-3:]

    lines = [
        "Sensor dataset context:",
        f"- Available CSV files: {SENSOR_DATASET['file_count']}",
        f"- Total raw rows across all files: {SENSOR_DATASET['row_count']}",
        f"- Date range: {SENSOR_DATASET['date_range'][0]} to {SENSOR_DATASET['date_range'][1]}",
        f"- Sensor IDs: {', '.join(sorted(sensor_id for sensor_id in SENSOR_DATASET['sensor_ids'] if sensor_id)) or 'unknown'}",
        f"- Selected columns for this question: {', '.join(selected_columns)}",
    ]

    lines.append("- Overall stats across all raw files:")
    for column in selected_columns:
        stats = SENSOR_DATASET["global_stats"].get(column)
        if not stats or stats["count"] == 0:
            continue
        avg = stats["sum"] / stats["count"]
        lines.append(
            f"  {column}: avg={_format_stat_value(avg)} min={_format_stat_value(stats['min'])} max={_format_stat_value(stats['max'])} count={stats['count']}"
        )

    lines.append("- Daily file summaries used for this question:")
    for sensor_file in chosen_files:
        lines.append("  " + _summarize_sensor_file(sensor_file, selected_columns))

    lines.append("- Raw row excerpts selected from the matching files:")
    for sensor_file in chosen_files:
        rows = sensor_file["rows"]
        sample_rows = []
        if rows:
            sample_rows.append(rows[0])
            if len(rows) > 2:
                sample_rows.append(rows[len(rows) // 2])
            if len(rows) > 1:
                sample_rows.append(rows[-1])

        best_column = selected_columns[0]
        best_max_row = None
        best_min_row = None
        numeric_rows = [row for row in rows if _safe_float(row.get(best_column)) is not None]
        if numeric_rows:
            best_max_row = max(numeric_rows, key=lambda row: _safe_float(row.get(best_column)))
            best_min_row = min(numeric_rows, key=lambda row: _safe_float(row.get(best_column)))

        for candidate in [best_max_row, best_min_row]:
            if candidate and candidate not in sample_rows:
                sample_rows.append(candidate)

        seen_timestamps = set()
        lines.append(f"  File {sensor_file['filename']} ({sensor_file['row_count']} rows total):")
        for row in sample_rows:
            timestamp = row.get("UTCDateTime")
            if not timestamp or timestamp in seen_timestamps:
                continue
            seen_timestamps.add(timestamp)
            row_bits = [f"UTCDateTime={timestamp}"]
            for column in selected_columns:
                value = row.get(column)
                if value not in (None, ""):
                    row_bits.append(f"{column}={value}")
            lines.append("    " + "; ".join(row_bits))

    if requested_dates:
        missing_dates = [date for date in requested_dates if date not in SENSOR_DATASET["by_date"]]
        if missing_dates:
            lines.append(f"- Requested dates not found in the dataset: {', '.join(missing_dates)}")

    lines.append(
        "- Important: these summaries and excerpts were computed by searching all loaded raw CSV sensor files on the server. If the question asks for a specific date or metric, prioritize the matching file stats and raw rows above."
    )

    context = "\n".join(lines)
    if len(context) > MAX_SENSOR_CONTEXT_CHARS:
        context = context[:MAX_SENSOR_CONTEXT_CHARS] + "\n[Sensor dataset context truncated.]"
    return context


def _normalize_chat_history(history):
    normalized = []
    for item in history or []:
        role = (item or {}).get("role")
        content = ((item or {}).get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized[-MAX_CHAT_HISTORY_MESSAGES:]


def _extract_response_text(response_payload):
    output_text = (response_payload or {}).get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    for item in (response_payload or {}).get("output", []):
        if item.get("type") != "message":
            continue
        text_parts = []
        for content_item in item.get("content", []):
            if content_item.get("type") == "output_text" and content_item.get("text"):
                text_parts.append(content_item["text"])
        text = "".join(text_parts).strip()
        if text:
            return text

    return ""


def _build_chat_input(history, message, page_title="", page_path=""):
    sensor_context = _build_sensor_dataset_context(message)
    page_context = []
    if page_title:
        page_context.append(f"Page title: {page_title}")
    if page_path:
        page_context.append(f"Page path: {page_path}")

    user_message = message.strip()
    if page_context:
        user_message += "\n\nCurrent page context:\n" + "\n".join(page_context)

    response_input = [
        {
            "role": "developer",
            "content": [{"type": "input_text", "text": CHATBOT_SYSTEM_PROMPT}],
        },
        {
            "role": "developer",
            "content": [{"type": "input_text", "text": sensor_context}],
        }
    ]

    for item in history:
        response_input.append({
            "role": item["role"],
            "content": [{"type": "input_text", "text": item["content"]}],
        })

    response_input.append({
        "role": "user",
        "content": [{"type": "input_text", "text": user_message}],
    })
    return response_input


def _create_openai_response(response_input):
    payload = json.dumps({
        "model": OPENAI_MODEL,
        "input": response_input,
    }).encode("utf-8")

    req = urllib_request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_openai_error_message(error_body):
    if not error_body:
        return ""

    try:
        payload = json.loads(error_body)
    except json.JSONDecodeError:
        return ""

    error_info = payload.get("error") or {}
    code = (error_info.get("code") or "").strip()
    message = (error_info.get("message") or "").strip()

    if code == "insufficient_quota":
        return "The OpenAI account has no available quota right now. Check billing, credits, and project limits."
    if code == "invalid_api_key":
        return "The OpenAI API key is invalid. Update OPENAI_API_KEY and restart the server."
    if "model" in message.lower() and "not found" in message.lower():
        return "The configured OpenAI model is unavailable. Check OPENAI_MODEL and restart the server."

    return message


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


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    page_title = (data.get("pageTitle") or "").strip()
    page_path = (data.get("pagePath") or "").strip()

    if not message:
        return jsonify({"success": False, "error": "Please enter a message."}), 400

    if not OPENAI_API_KEY:
        return jsonify({
            "success": False,
            "error": "Chatbot is not configured yet. Add OPENAI_API_KEY to the server environment.",
        }), 500

    history = _normalize_chat_history(session.get(CHAT_HISTORY_SESSION_KEY, []))
    response_input = _build_chat_input(history, message, page_title, page_path)

    try:
        response_payload = _create_openai_response(response_input)
        reply = _extract_response_text(response_payload)
    except urllib_error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8")
        except Exception:
            error_body = ""
        print(f"OpenAI API HTTP error: {exc.code} {error_body}")
        friendly_message = _extract_openai_error_message(error_body)
        return jsonify({
            "success": False,
            "error": friendly_message or "The assistant could not respond right now. Please try again in a moment.",
        }), 502
    except Exception as exc:
        print(f"OpenAI API request failed: {exc}")
        return jsonify({
            "success": False,
            "error": "The assistant is temporarily unavailable. Please try again later.",
        }), 502

    if not reply:
        return jsonify({
            "success": False,
            "error": "The assistant returned an empty response. Please try again.",
        }), 502

    history.extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ])
    session[CHAT_HISTORY_SESSION_KEY] = history[-MAX_CHAT_HISTORY_MESSAGES:]

    return jsonify({"success": True, "reply": reply}), 200


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

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    report_id = uuid.uuid4().hex[:12]

    report = {
        "id": report_id,
        "title": title,
        "description": description,
        "severity": severity,
        "status": "open",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    if USE_FIREBASE:
        try:
            db.collection('bug_reports').document(report_id).set(report)
        except Exception as e:
            print(f"Firebase save error: {e}")
            return jsonify({"success": False, "error": "Failed to save report"}), 500
    else:
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
    return jsonify({"success": True, "reports": reports}), 200


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

    if USE_FIREBASE:
        try:
            doc_ref = db.collection('bug_reports').document(report_id)
            doc_ref.update({"status": new_status})
            # Get the updated document
            updated_doc = doc_ref.get()
            if updated_doc.exists:
                return jsonify({"success": True, "report": updated_doc.to_dict()}), 200
            else:
                return jsonify({"success": False, "error": "Report not found."}), 404
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    else:
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
    if USE_FIREBASE:
        try:
            doc_ref = db.collection('bug_reports').document(report_id)
            doc = doc_ref.get()
            if not doc.exists:
                return jsonify({"success": False, "error": "Report not found."}), 404
            
            doc_ref.delete()
            return jsonify({"success": True}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        reports = _load_bug_reports()
        remaining = [r for r in reports if r.get("id") != report_id]
        if len(remaining) == len(reports):
            return jsonify({"success": False, "error": "Report not found."}), 404

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
