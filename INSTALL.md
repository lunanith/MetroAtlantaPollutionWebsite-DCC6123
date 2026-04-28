# Installation Guide
**Metro Atlanta Pollution Website**
**Team DCC-6123 | AI-Driven / GIS-Based Research & Educational Support Tool**

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Dependent Libraries](#2-dependent-libraries)
3. [Download Instructions](#3-download-instructions)
4. [Build Instructions](#4-build-instructions)
5. [Installation](#5-installation)
6. [Run Instructions](#6-run-instructions)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites

Before beginning, ensure your system meets the following requirements:

**Software:**
- **Python 3.9 or higher** — [Download Python](https://www.python.org/downloads/)
- **pip** (Python package manager, included with Python 3.9+) — [pip documentation](https://pip.pypa.io/en/stable/installation/)
- **Git** — [Download Git](https://git-scm.com/downloads)
- A modern web browser (Google Chrome, Firefox, or Edge recommended)

**Accounts / API Access:**
- A **Firebase** project with Firestore and Firebase Auth enabled — [Get started with Firebase](https://firebase.google.com/docs/web/setup)
- An **ArcGIS** developer account or ArcGIS API key — [ArcGIS Developers](https://developers.arcgis.com/)
- An **AI API key** for the chatbot integration (see your team's API provider setup)

**Hardware:**
- Any modern computer running Windows, macOS, or Linux
- Minimum 4 GB RAM recommended
- Active internet connection required (for ArcGIS map, Firebase, and AI chatbot)

---

## 2. Dependent Libraries

All Python dependencies are listed in `requirements.txt` at the root of the repository. Key dependencies include:

- **Flask** — web server framework
- **Firebase Admin SDK** — backend Firebase integration
- Any AI API client library used for chatbot integration

To install all dependencies at once, see [Build Instructions](#4-build-instructions) below.

---

## 3. Download Instructions

Clone the repository from GitHub using Git:

```bash
git clone https://github.com/lunanith/MetroAtlantaPollutionWebsite-DCC6123.git
cd MetroAtlantaPollutionWebsite-DCC6123
```

Alternatively, you can download the repository as a ZIP file directly from GitHub:

1. Go to [https://github.com/lunanith/MetroAtlantaPollutionWebsite-DCC6123](https://github.com/lunanith/MetroAtlantaPollutionWebsite-DCC6123)
2. Click the green **Code** button → **Download ZIP**
3. Extract the ZIP to your desired directory and navigate into it

---

## 4. Build Instructions

This project does not require compilation. However, you must install the required Python packages before running the application.

**Step 1 — Create a virtual environment (recommended):**

```bash
python -m venv venv
```

Activate the virtual environment:

- **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```
- **Windows:**
  ```bash
  venv\Scripts\activate
  ```

**Step 2 — Install dependencies:**

```bash
pip install -r requirements.txt
```

**Step 3 — Configure environment variables:**

A `.env.example` file is provided in the root of the repository. Copy it and fill in your own credentials:

```bash
cp .env.example .env
```

Then open `.env` and replace each placeholder with your actual values:

```dotenv
SENDER_EMAIL=your_sender_gmail@gmail.com
SENDER_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=info@csc-atl.org
FIREBASE_CREDENTIALS_PATH=/path/to/your/firebase-credentials.json
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
```

**Notes on each variable:**

- **`SENDER_EMAIL`** — the Gmail address the application uses to send contact form and bug report submissions. Must use an App Password rather than a regular Gmail password (see below). Note: ownership of the original account used from the development team will be transferred to the client at handoff.
- **`SENDER_PASSWORD`** — a Gmail **App Password** for the sender account, not a regular Gmail password. To generate one: go to your Google Account → Security → 2-Step Verification → App Passwords. [Guide here](https://support.google.com/accounts/answer/185833).
- **`RECIPIENT_EMAIL`** — the CSC-ATL inbox that receives all contact form submissions. This value is fixed and should remain `info@csc-atl.org`.
- **`FIREBASE_CREDENTIALS_PATH`** — the local file path to your Firebase service account JSON file. To obtain this file: go to the [Firebase Console](https://console.firebase.google.com/) → select the project → Project Settings → Service Accounts → **Generate New Private Key**. Save the downloaded JSON file somewhere on your machine and set this variable to that file's full path (e.g., `C:\Users\yourname\Documents\firebase-credentials.json` on Windows or `/home/yourname/firebase-credentials.json` on Mac/Linux).
- **`OPENAI_API_KEY`** — your OpenAI API key. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
- **`OPENAI_MODEL`** — the OpenAI model name to use for the chatbot (e.g., `gpt-4o-mini`).

> ⚠️ **Never commit your `.env` file to GitHub.** It is already listed in `.gitignore`. Only commit `.env.example` with placeholder values.

---

## 5. Installation

No additional installation steps are required beyond the dependency setup above. All static frontend files (HTML, CSS, JavaScript) are served directly by Flask from the `public/` and `docs/` directories. No build tools, bundlers, or compilers are needed.

Ensure the following directory structure is intact after cloning:

```
MetroAtlantaPollutionWebsite-DCC6123/
├── public/          # Frontend HTML, CSS, JS assets
├── docs/            # Additional documentation assets
├── app.py           # Flask application entry point
├── requirements.txt # Python dependencies
└── .env             # Your local environment variables (not tracked by git)
```

---

## 6. Run Instructions

**Start the Flask development server:**

```bash
python app.py
```

Once running, you should see output similar to:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

**Open the application:**

Open your browser and navigate to:

```
http://127.0.0.1:5000
```

The homepage should load with the navigation bar and CSC-ATL content visible.

> **Note:** The ArcGIS map, chatbot, and contact form all require an active internet connection and valid API keys to function correctly.

---

## 7. Troubleshooting

**`ModuleNotFoundError` when running `app.py`**

You likely skipped the dependency install step or your virtual environment is not activated. Run:

```bash
pip install -r requirements.txt
```

Make sure your virtual environment is active before running the above command.

---

**Flask server starts but the browser shows a blank page or 404**

Ensure you are navigating to `http://127.0.0.1:5000` (not `https://`). Also verify that the `public/` directory exists and contains the HTML files.

---

**ArcGIS map does not load**

- Confirm your `ARCGIS_API_KEY` is set correctly in your `.env` file.
- Check that your ArcGIS account has an active subscription or developer tier with map tile access.
- Some corporate or school networks may block ArcGIS tile requests. In this case, try on a different network.

---

**Chatbot does not respond**

- Verify your `AI_API_KEY` is set correctly in your `.env` file.
- Check your API provider dashboard to confirm your key is active and has remaining quota.
- On first load, the chatbot may take several seconds to initialize. In this case, wait a moment before sending a message.

---

**Firebase authentication or Firestore errors**

- Confirm all Firebase credentials in `.env` match those in your Firebase project console.
- Make sure Firestore and Firebase Auth are enabled in your Firebase project settings.
- Check that your Firebase project's security rules allow read/write access as needed.

---

**Contact form or bug report form submissions are not received**

- Confirm the Flask server is running and no errors appear in the terminal.
- Check that your Firebase Firestore connection is active and the collection names match what is configured in `app.py`.

---

*For questions or support, contact the CSC-ATL team via the Contact page on the website.*
