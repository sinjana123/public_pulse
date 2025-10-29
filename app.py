
from flask import Flask, request, jsonify, send_from_directory, g, session
import os
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "..", "public pulse website")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "publicpulse.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
# IMPORTANT: In production set a secure random secret key via environment var
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

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

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({"error":"unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

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
    return jsonify({"status":"ok","issue_id":issue_id})

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json() or request.form
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    if not name or not email or not message:
        return jsonify({"error":"name,email,message required"}), 400
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO contacts (name,email,message) VALUES (?,?,?)", (name,email,message))
    db.commit()
    return jsonify({"status":"ok"})

@app.route('/api/vote', methods=['POST'])
def vote():
    data = request.get_json() or request.form
    title = data.get('title')
    if not title:
        return jsonify({"error":"title required"}), 400
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM issues WHERE title = ?", (title,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE issues SET votes = votes + 1 WHERE id = ?", (row['id'],))
        db.commit()
        return jsonify({"status":"ok","action":"incremented"})
    else:
        cur.execute("INSERT INTO issues (title,description,location,votes,status) VALUES (?,?,?,?,?)", 
                    (title, '', '', 1, 'Pending'))
        db.commit()
        return jsonify({"status":"ok","action":"created"})

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

# ---------------- Admin auth & dashboard APIs ----------------

@app.route('/api/admin/create', methods=['POST'])
def create_admin():
    data = request.get_json() or request.form
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"error":"email and password required"}), 400
    pw_hash = generate_password_hash(password)
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("INSERT INTO admins (email,password_hash) VALUES (?,?)", (email,pw_hash))
        db.commit()
        return jsonify({"status":"ok"})
    except Exception as e:
        db.rollback()
        return jsonify({"error":str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or request.form
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"error":"email and password required"}), 400
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id,password_hash FROM admins WHERE email = ?", (email,))
    row = cur.fetchone()
    if not row or not check_password_hash(row['password_hash'], password):
        return jsonify({"error":"invalid credentials"}), 401
    session['admin_logged_in'] = True
    session['admin_id'] = row['id']
    session['admin_email'] = email
    return jsonify({"status":"ok"})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    return jsonify({"status":"ok"})

@app.route('/api/admin/session', methods=['GET'])
def admin_session():
    if session.get('admin_logged_in'):
        return jsonify({"logged_in":True,"email":session.get('admin_email')})
    return jsonify({"logged_in":False})

@app.route('/api/admin/reports', methods=['GET'])
@admin_required
def admin_reports():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id,title,description,location,votes,status,photo_path,created_at FROM issues ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if r.get('photo_path'):
            r['photo_url'] = '/uploads/' + os.path.basename(r['photo_path'])
        else:
            r['photo_url'] = None
    return jsonify(rows)

@app.route('/api/admin/contacts', methods=['GET'])
@admin_required
def admin_contacts():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id,name,email,message,created_at FROM contacts ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

@app.route('/api/admin/update_status', methods=['POST'])
@admin_required
def admin_update_status():
    data = request.get_json() or request.form
    issue_id = data.get('issue_id')
    status = data.get('status')
    if not issue_id or not status:
        return jsonify({"error":"issue_id and status required"}), 400
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE issues SET status = ? WHERE id = ?", (status, issue_id))
    db.commit()
    cur.execute("INSERT INTO reports_log (issue_id, action) VALUES (?,?)", (issue_id, 'status:' + status))
    db.commit()
    return jsonify({"status":"ok"})

# Serve frontend static files (index, css, js)
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_file(path):
    safe_path = os.path.join(STATIC_DIR, path)
    # Protect admin path: serve admin.html only if logged in otherwise serve login.html
    if path.startswith('admin'):
        if session.get('admin_logged_in'):
            return send_from_directory(STATIC_DIR, 'admin.html')
        else:
            return send_from_directory(STATIC_DIR, 'login.html')
    if os.path.exists(safe_path):
        return send_from_directory(STATIC_DIR, path)
    # fallback to index
    return send_from_directory(STATIC_DIR, 'index.html')
@app.route("/admin")
def admin_panel():
    return "<h1>Welcome to the Admin Dashboard</h1><p>Backend is working perfectly!</p>"
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)


