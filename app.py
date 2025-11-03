from flask import Flask, send_from_directory, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

app = Flask(__name__)
app.secret_key = os.environ.get('APP_SECRET_KEY', 'dev-secret-key-change-me')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


# Initialize database at startup
init_db()


@app.route("/")
def login_page():
    # Serve login.html from project root
    return send_from_directory(".", "login.html")


@app.route('/<path:filename>')
def serve_file(filename):
    # Serve static files like local_auth.js, images, etc.
    return send_from_directory(".", filename)


# Convenience route to serve frontpage.html from templates if present
@app.get('/frontpage.html')
def serve_frontpage():
    try:
        return send_from_directory("templates", "frontpage.html")
    except Exception:
        # Fallback to project root if someone placed it there
        return send_from_directory(".", "frontpage.html")


@app.post('/api/register')
def api_register():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    full_name = (data.get('fullName') or '').strip()
    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"ok": False, "error": "Password must be at least 6 characters."}), 400

    password_hash = generate_password_hash(password)
    created_at = datetime.utcnow().isoformat()
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (full_name, email, password_hash, created_at)
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "Email already exists."}), 409

    return jsonify({"ok": True}), 201


@app.post('/api/login')
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password are required."}), 400

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"ok": False, "error": "Invalid email or password."}), 401
    # Set simple session
    session['user_email'] = user['email']
    session['full_name'] = user['full_name']

    return jsonify({"ok": True, "user": {"email": user['email'], "fullName": user['full_name']}})


@app.post('/api/forgot')
def api_forgot():
    # Placeholder for password reset email flow
    return jsonify({"ok": True})


@app.post('/api/logout')
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get('/api/me')
def api_me():
    email = session.get('user_email')
    full_name = session.get('full_name')
    if not email:
        return jsonify({"ok": False}), 401
    return jsonify({"ok": True, "user": {"email": email, "fullName": full_name}})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5173, debug=True)