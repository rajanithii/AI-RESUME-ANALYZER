import os, sqlite3, json, hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

# 1. Imports
try:
    from utils.resume_parser import parse_resume
    from utils.skill_extractor import extract_skills
    from utils.recommender import recommend_careers
except ImportError:
    from project2.utils.resume_parser import parse_resume
    from project2.utils.skill_extractor import extract_skills
    from project2.utils.recommender import recommend_careers

import nltk
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# 2. Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

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
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL, full_name TEXT, phone TEXT, location TEXT, dob TEXT, gender TEXT, linkedin TEXT, github TEXT, bio TEXT, degree TEXT, college TEXT, graduation_year TEXT, job_title TEXT, experience_years TEXT, avatar_color TEXT DEFAULT '#6EE7F7', updated_at TEXT, FOREIGN KEY (user_id) REFERENCES users(id))")
    c.execute("CREATE TABLE IF NOT EXISTS resumes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT NOT NULL, upload_time TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id))")
    c.execute("CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY AUTOINCREMENT, resume_id INTEGER, skill TEXT NOT NULL, FOREIGN KEY (resume_id) REFERENCES resumes(id))")
    c.execute("CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY AUTOINCREMENT, resume_id INTEGER, career TEXT NOT NULL, match_percentage REAL, missing_skills TEXT, FOREIGN KEY (resume_id) REFERENCES resumes(id))")
    conn.commit()
    conn.close()

# CRITICAL: This must be outside the if block for Render
init_db()

# --- AUTH HELPERS ---
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
    if "user_id" not in session: return None
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
        if len(parts) >= 2: return (parts[0][0] + parts[-1][0]).upper()
        return parts[0][0].upper()
    return username[0].upper() if username else "U"

def serialize_recommendations(recommendations):
    result = []
    for rec in recommendations:
        result.append({
            "career": rec["career"],
            "match_percentage": rec["match_percentage"],
            "matched_skills": sorted(list(rec.get("matched_skills", []))),
            "missing_skills": sorted(list(rec.get("missing_skills", []))),
        })
    return result

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---
@app.route("/")
def home():
    return redirect(url_for("dashboard")) if "user_id" in session else redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session: return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password_hash=?", (email, hash_password(password))).fetchone()
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
        username, email, password, confirm = request.form.get("username"), request.form.get("email"), request.form.get("password"), request.form.get("confirm")
        if password != confirm: error = "Passwords do not match."
        else:
            try:
                conn = get_db()
                conn.execute("INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)", (username, email, hash_password(password), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute("INSERT INTO profiles (user_id, full_name, updated_at) VALUES (?,?,?)", (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError: error = "User already exists."
    return render_template("register.html", error=error)

@app.route("/dashboard")
@login_required
def dashboard():
    user, profile = get_current_user(), get_profile(session["user_id"])
    conn = get_db()
    resumes = conn.execute("SELECT * FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 10", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("dashboard.html", user=user, profile=profile, initials=get_initials(profile["full_name"], user["username"]), resumes=resumes)

@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    if "resume" not in request.files: return redirect(request.url)
    file = request.files["resume"]
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        resume_text = parse_resume(file_path)
        if not resume_text: return "Error parsing resume."
        skills = extract_skills(resume_text)
        recommendations = recommend_careers(skills)
        recs_clean = serialize_recommendations(recommendations)
        conn = get_db()
        conn.execute("INSERT INTO resumes (user_id, filename, upload_time) VALUES (?,?,?)", (session["user_id"], filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        resume_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit(); conn.close()
        session.update({"skills": skills, "recommendations": recs_clean, "filename": filename})
        return redirect(url_for("result"))
    return "Invalid file type."

@app.route("/result")
@login_required
def result():
    user, profile = get_current_user(), get_profile(session["user_id"])
    return render_template("result.html", user=user, profile=profile, initials=get_initials(profile["full_name"], user["username"]), skills=session.get("skills", []), recommendations=session.get("recommendations", []), filename=session.get("filename", ""))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Ensure double underscores here:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
