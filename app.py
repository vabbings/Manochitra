from flask import Flask, send_from_directory

app = Flask(__name__)

# Serve the login page from the project root (where login.html lives)
@app.route("/")
def login_page():
    return send_from_directory(".", "login.html")

# Serve other files in the project root (e.g., auth.js, css, images)
@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(".", filename)

app.run(host='0.0.0.0', port=5173, debug=True)