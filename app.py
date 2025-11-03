from flask import Flask, request, jsonify, render_template, session, redirect, send_from_directory, make_response

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'  # Change this in production!

@app.route("/")
def login_page():
    """Login page route"""
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    """Sign up page route"""
    return render_template("signup.html")

@app.route("/frontpage")
def frontpage():
    """Frontpage route - protected by Firebase on client side"""
    return render_template("frontpage.html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5173, debug=True)