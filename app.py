import os, sqlite3, json, hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

# ── Utils import (works both locally and on Render) ──────────────────────────
import sys
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Make sure the project root is always on the path so `utils` is importable
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.resume_parser import parse_resume
from utils.skill_extractor import extract_skills
from utils.recommender import recommend_careers

# ── NLTK bootstrap ───────────────────────────────────────────────────────────
import nltk

def _ensure_nltk(resource_path, download_name):
    try:
        nltk.data.find(resource_path)
    except LookupError:
        nltk.download(download_name, quiet=True)

_ensure_nltk('corpora/stopwords',   'stopwords')
_ensure_nltk('tokenizers/punkt',    'punkt')
# newer NLTK (3.8+) also needs punkt_tab
try:
    _ensure_nltk('tokenizers/punkt_tab', 'punkt_tab')
except Exception:
    pass

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

app.secret_key = "resumeai_ultra_secret_2024_xK9p"

ALLOWED_EXTENSIONS = {"pdf", "docx"}
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATABASE = os.path.join(BASE_DIR, "database.db")

# ══════════════════════════════════════════════════════
#  DATABASE SETUP
# ══════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        full_name TEXT, phone TEXT, location TEXT, dob TEXT, gender TEXT,
        linkedin TEXT, github TEXT, bio TEXT, degree TEXT, college TEXT,
        graduation_year TEXT, job_title TEXT, experience_years TEXT,
        avatar_color TEXT DEFAULT '#6EE7F7', updated_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT NOT NULL,
        upload_time TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id INTEGER,
        skill TEXT NOT NULL,
        FOREIGN KEY (resume_id) REFERENCES resumes(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id INTEGER,
        career TEXT NOT NULL,
        match_percentage REAL,
        missing_skills TEXT,
        FOREIGN KEY (resume_id) REFERENCES resumes(id)
    )""")
    conn.commit()
    conn.close()

init_db()

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user

def get_profile(user_id):
    conn = get_db()
    profile = conn.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return profile

def get_initials(name, username):
    if name:
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return parts[0][0].upper()
    return username[0].upper() if username else "U"

def serialize_recommendations(recommendations):
    result = []
    for rec in recommendations:
        matched = sorted(list(rec.get("matched_skills", [])))
        missing = sorted(list(rec.get("missing_skills", [])))
        result.append({
            "career": rec["career"],
            "match_percentage": rec["match_percentage"],
            "matched_skills": matched,
            "missing_skills": missing,
            # total_matched used in result.html template
            "total_matched": len(matched),
        })
    return result

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ══════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password_hash=?",
            (email, hash_password(password))
        ).fetchone()
        conn.close()
        if user:
            session.update({"user_id": user["id"], "username": user["username"], "email": user["email"]})
            return redirect(url_for("dashboard"))
        error = "Invalid email or password."
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        if password != confirm:
            error = "Passwords do not match."
        else:
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)",
                    (username, email, hash_password(password), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute(
                    "INSERT INTO profiles (user_id, full_name, updated_at) VALUES (?,?,?)",
                    (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                conn.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username or email already exists."
    return render_template("register.html", error=error)

@app.route("/dashboard")
@login_required
def dashboard():
    user    = get_current_user()
    profile = get_profile(session["user_id"])
    conn    = get_db()
    resumes = conn.execute(
        "SELECT * FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template(
        "dashboard.html",
        user=user, profile=profile,
        initials=get_initials(profile["full_name"] if profile else None, user["username"]),
        resumes=resumes
    )

@app.route("/upload")
@login_required
def upload():
    return render_template("upload.html")

@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    if "resume" not in request.files:
        return redirect(url_for("dashboard"))

    file = request.files["resume"]
    if not file or not allowed_file(file.filename):
        return render_template("upload.html", error="Please upload a valid PDF or DOCX file.")

    filename  = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    try:
        resume_text = parse_resume(file_path)
        if not resume_text:
            return render_template("upload.html", error="Could not extract text from your resume. Please try a different file.")

        skills          = extract_skills(resume_text)
        recommendations = recommend_careers(skills)
        recs_clean      = serialize_recommendations(recommendations)

        conn = get_db()
        conn.execute(
            "INSERT INTO resumes (user_id, filename, upload_time) VALUES (?,?,?)",
            (session["user_id"], filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

        session["skills"]           = skills
        session["recommendations"]  = recs_clean
        session["filename"]         = filename

        return redirect(url_for("result"))

    except Exception as e:
        app.logger.error(f"Analysis error: {e}")
        return render_template("upload.html", error=f"Analysis failed: {str(e)}")

@app.route("/result")
@login_required
def result():
    user    = get_current_user()
    profile = get_profile(session["user_id"])
    return render_template(
        "result.html",
        user=user, profile=profile,
        initials=get_initials(profile["full_name"] if profile else None, user["username"]),
        skills=session.get("skills", []),
        recommendations=session.get("recommendations", []),
        filename=session.get("filename", "")
    )

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user    = get_current_user()
    prof    = get_profile(session["user_id"])
    success = False
    error   = None

    if request.method == "POST":
        fields = ["full_name", "phone", "location", "dob", "gender",
                  "linkedin", "github", "bio", "degree", "college",
                  "graduation_year", "job_title", "experience_years"]
        values = {f: request.form.get(f, "").strip() for f in fields}
        try:
            conn = get_db()
            conn.execute("""UPDATE profiles SET
                full_name=?, phone=?, location=?, dob=?, gender=?,
                linkedin=?, github=?, bio=?, degree=?, college=?,
                graduation_year=?, job_title=?, experience_years=?, updated_at=?
                WHERE user_id=?""",
                (*[values[f] for f in fields],
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 session["user_id"])
            )
            conn.commit()
            conn.close()
            prof    = get_profile(session["user_id"])
            success = True
        except Exception as e:
            error = str(e)

    return render_template(
        "profile.html",
        user=user, profile=prof,
        initials=get_initials(prof["full_name"] if prof else None, user["username"]),
        success=success, error=error
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ══════════════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
