from flask import Flask, request, jsonify, send_from_directory, g, session
import os
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")  # ✅ Fix this line
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "publicpulse.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

# ---------------- Database ----------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE,
        description TEXT,
        location TEXT,
        photo_path TEXT,
        votes INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reports_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id INTEGER,
        action TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password_hash TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db.commit()

# ---------------- Auth Helper ----------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ---------------- API Routes ----------------
@app.route('/api/report', methods=['POST'])
def submit_report():
    title = request.form.get('title')
    description = request.form.get('description')
    location = request.form.get('location')
    file = request.files.get('photo')
    if not title or not description:
        return jsonify({"error": "title and description required"}), 400

    photo_path = None
    if file:
        filename = secure_filename(file.filename)
        filename = secrets.token_hex(8) + "_" + filename
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(photo_path)

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""INSERT INTO issues (title, description, location, photo_path, status)
                       VALUES (?,?,?,?,?)""", (title, description, location, photo_path, 'Pending'))
        db.commit()
        issue_id = cur.lastrowid
        cur.execute("INSERT INTO reports_log (issue_id, action) VALUES (?,?)", (issue_id, 'created'))
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "issue_id": issue_id})

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json() or request.form
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    if not name or not email or not message:
        return jsonify({"error": "name,email,message required"}), 400
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO contacts (name,email,message) VALUES (?,?,?)", (name,email,message))
    db.commit()
    return jsonify({"status": "ok"})

@app.route('/api/vote', methods=['POST'])
def vote():
    data = request.get_json() or request.form
    title = data.get('title')
    if not title:
        return jsonify({"error": "title required"}), 400
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM issues WHERE title = ?", (title,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE issues SET votes = votes + 1 WHERE id = ?", (row['id'],))
        db.commit()
        return jsonify({"status": "ok", "action": "incremented"})
    else:
        cur.execute("INSERT INTO issues (title, description, location, votes, status) VALUES (?,?,?,?,?)",
                    (title, '', '', 1, 'Pending'))
        db.commit()
        return jsonify({"status": "ok", "action": "created"})

@app.route('/api/issues', methods=['GET'])
def list_issues():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id,title,description,location,votes,status,photo_path,created_at FROM issues ORDER BY votes DESC, created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if r.get('photo_path'):
            r['photo_url'] = '/uploads/' + os.path.basename(r['photo_path'])
        else:
            r['photo_url'] = None
    return jsonify(rows)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------- Admin Routes ----------------
@app.route("/admin")
def admin_panel():
    return "<h1>Welcome to the Admin Dashboard</h1><p>Backend is working perfectly!</p>"

# ---------------- Frontend Routing ----------------
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_file(path):
    target = path if path else 'index.html'
    safe_path = os.path.join(STATIC_DIR, target)
    if os.path.exists(safe_path):
        return send_from_directory(STATIC_DIR, target)
    return send_from_directory(STATIC_DIR, 'index.html')

# ---------------- Main ----------------
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
