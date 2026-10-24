# TECHNERD Quiz — Flask starter project

A runnable starter for the TECHNERD live technical quiz using **HTML, CSS, JavaScript, Python (Flask), and SQLite**. The visual style follows the supplied TECH PULSE poster: dark navy, neon cyan, blue and purple.

## Features
- Participant join page using an event code.
- Live quiz page with timer and automatic refresh.
- Three admin logins, question creation and deletion.
- Start/resume, pause, next question, end quiz, and reset scores.
- Server-side answer validation and score calculation.
- Leaderboard refreshes automatically.
- SQLite database is created automatically and seeded with sample questions.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create a virtual environment (recommended):
   - Windows: `py -m venv .venv`
   - Windows: `.venv\Scripts\activate`
4. Install packages: `pip install -r requirements.txt`
5. Start: `python app.py`
6. Open `http://127.0.0.1:5000`

## Demo accounts
- `admin1` / `Technerd@123`
- `admin2` / `Technerd@123`
- `admin3` / `Technerd@123`

Default event code: `TECH2026`.

## Important before using with real participants
This is a starter/demo, not yet a hardened production deployment.
- Change all three demo admin passwords and set a strong `SECRET_KEY`.
- Set `TECHNERD_EVENT_CODE` to your own event code.
- Run behind a production WSGI server (e.g. Waitress on Windows or Gunicorn on Linux); do not use Flask debug mode in production.
- Add CSRF protection, rate limiting, admin password-change flow, and stricter session/security settings before public launch.
- For a multi-computer live event, deploy to a server reachable by participants. `127.0.0.1` only serves the computer running the app.
- This starter uses SQLite. For a large concurrent event, consider PostgreSQL and a proper synchronized round schedule.
- Admin access is shared by role; any admin can control the event and reset scores. Restrict who receives the credentials.
- The event code is a simple gate, not identity verification.
