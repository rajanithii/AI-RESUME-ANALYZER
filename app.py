"""


app.py — ResumeAI Full Stack
Includes: Auth (login/register), Profile, Resume Analysis Dashboard
"""

import os, sqlite3, json, hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from utils.resume_parser import parse_resume
from utils.skill_extractor import extract_skills
from utils.recommender import recommend_careers

app = Flask(__name__)
app.secret_key = "resumeai_ultra_secret_2024_xK9p"

ALLOWED_EXTENSIONS = {"pdf", "docx"}
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = os.path.join(os.path.dirname(__file__), "database.db")


# ══════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode = WAL;")
    # Set busy timeout to 30 seconds
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Profile table (one-to-one with users)
    c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT,
            phone TEXT,
            location TEXT,
            dob TEXT,
            gender TEXT,
            linkedin TEXT,
            github TEXT,
            bio TEXT,
            degree TEXT,
            college TEXT,
            graduation_year TEXT,
            job_title TEXT,
            experience_years TEXT,
            avatar_color TEXT DEFAULT '#6EE7F7',
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Resumes table (linked to user)
    c.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Skills table
    c.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER,
            skill TEXT NOT NULL,
            FOREIGN KEY (resume_id) REFERENCES resumes(id)
        )
    """)

    # Recommendations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER,
            career TEXT NOT NULL,
            match_percentage REAL,
            missing_skills TEXT,
            FOREIGN KEY (resume_id) REFERENCES resumes(id)
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Initialized.")


def hash_password(password):
    """Simple SHA-256 hash for password storage."""
    return hashlib.sha256(password.encode()).hexdigest()


# ══════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════

def login_required(f):
    """Decorator — redirects to login if user not in session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Returns current logged-in user row, or None."""
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user


def get_profile(user_id):
    """Returns profile row for given user_id, or None."""
    conn = get_db()
    profile = conn.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return profile


def get_initials(name, username):
    """Get avatar initials from full name or username."""
    if name:
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return parts[0][0].upper()
    return username[0].upper() if username else "U"


def serialize_recommendations(recommendations):
    """Convert sets → lists for JSON session storage."""
    result = []
    for rec in recommendations:
        result.append({
            "career":           rec["career"],
            "match_percentage": rec["match_percentage"],
            "matched_skills":   sorted(list(rec.get("matched_skills", []))),
            "missing_skills":   sorted(list(rec.get("missing_skills", []))),
            "total_required":   rec.get("total_required", 0),
            "total_matched":    rec.get("total_matched", 0),
        })
    return result


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ══════════════════════════════════════════════════════
#  ROUTES — AUTH
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

        if not email or not password:
            error = "Please fill in all fields."
        else:
            conn = get_db()
            user = conn.execute(
                "SELECT * FROM users WHERE email=? AND password_hash=?",
                (email, hash_password(password))
            ).fetchone()
            conn.close()

            if user:
                session["user_id"]  = user["id"]
                session["username"] = user["username"]
                session["email"]    = user["email"]
                return redirect(url_for("dashboard"))
            else:
                error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not username or not email or not password or not confirm:
            error = "Please fill in all fields."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)",
                    (username, email, hash_password(password), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                # Create empty profile
                conn.execute(
                    "INSERT INTO profiles (user_id, full_name, updated_at) VALUES (?,?,?)",
                    (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                conn.close()
                return redirect(url_for("login") + "?registered=1")
            except sqlite3.IntegrityError:
                error = "Username or email already exists."

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════
#  ROUTES — PROFILE
# ══════════════════════════════════════════════════════

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user    = get_current_user()
    profile = get_profile(session["user_id"])
    success = False
    error   = None

    if request.method == "POST":
        fields = [
            "full_name", "phone", "location", "dob", "gender",
            "linkedin", "github", "bio", "degree", "college",
            "graduation_year", "job_title", "experience_years"
        ]
        values = {f: request.form.get(f, "").strip() for f in fields}
        values["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values["user_id"] = session["user_id"]

        try:
            conn = get_db()
            conn.execute("""
                UPDATE profiles SET
                    full_name=:full_name, phone=:phone, location=:location,
                    dob=:dob, gender=:gender, linkedin=:linkedin, github=:github,
                    bio=:bio, degree=:degree, college=:college,
                    graduation_year=:graduation_year, job_title=:job_title,
                    experience_years=:experience_years, updated_at=:updated_at
                WHERE user_id=:user_id
            """, values)
            conn.commit()
            conn.close()
            profile = get_profile(session["user_id"])
            success = True
        except Exception as e:
            error = str(e)

    initials = get_initials(profile["full_name"] if profile else None, user["username"])
    return render_template("profile.html",
                           user=user, profile=profile,
                           initials=initials,
                           success=success, error=error)


@app.route("/api/profile")
@login_required
def api_profile():
    """Returns profile JSON for the dropdown panel in dashboard."""
    user    = get_current_user()
    profile = get_profile(session["user_id"])
    initials = get_initials(
        profile["full_name"] if profile else None,
        user["username"]
    )
    data = {
        "username":    user["username"],
        "email":       user["email"],
        "initials":    initials,
        "full_name":   profile["full_name"]   if profile else "",
        "phone":       profile["phone"]       if profile else "",
        "location":    profile["location"]    if profile else "",
        "job_title":   profile["job_title"]   if profile else "",
        "college":     profile["college"]     if profile else "",
        "degree":      profile["degree"]      if profile else "",
        "linkedin":    profile["linkedin"]    if profile else "",
        "github":      profile["github"]      if profile else "",
        "bio":         profile["bio"]         if profile else "",
        "avatar_color":profile["avatar_color"] if profile else "#6EE7F7",
        "experience_years": profile["experience_years"] if profile else "",
        "graduation_year":  profile["graduation_year"]  if profile else "",
    }
    return jsonify(data)


# ══════════════════════════════════════════════════════
#  ROUTES — DASHBOARD & ANALYSIS
# ══════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard — shows upload form + recent analyses."""
    user     = get_current_user()
    profile  = get_profile(session["user_id"])
    initials = get_initials(profile["full_name"] if profile else None, user["username"])

    # Get user's recent resume analyses
    conn = get_db()
    resumes = conn.execute(
        "SELECT * FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    hour = datetime.now().hour
    greeting = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    return render_template("dashboard.html",
                           user=user, profile=profile,
                           initials=initials, resumes=resumes,
                           greeting=greeting)


@app.route("/upload")
@login_required
def upload():
    user     = get_current_user()
    profile  = get_profile(session["user_id"])
    initials = get_initials(profile["full_name"] if profile else None, user["username"])
    return render_template("upload.html", user=user, profile=profile, initials=initials)


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    user    = get_current_user()
    profile = get_profile(session["user_id"])
    initials = get_initials(profile["full_name"] if profile else None, user["username"])

    if "resume" not in request.files:
        return render_template("upload.html", user=user, profile=profile, initials=initials, error="No file in request.")

    file = request.files["resume"]
    if file.filename == "":
        return render_template("upload.html", user=user, profile=profile, initials=initials, error="No file selected.")
    if not allowed_file(file.filename):
        return render_template("upload.html", user=user, profile=profile, initials=initials, error="Upload PDF or DOCX only.")

    filename  = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    resume_text = parse_resume(file_path)
    if not resume_text:
        return render_template("upload.html", user=user, profile=profile, initials=initials, error="Could not read resume text. Try another file.")

    skills          = extract_skills(resume_text)
    recommendations = recommend_careers(skills, top_n=5)
    recs_clean      = serialize_recommendations(recommendations)

    # Save to DB linked to current user
    conn = get_db()
    conn.execute(
        "INSERT INTO resumes (user_id, filename, upload_time) VALUES (?,?,?)",
        (session["user_id"], filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    resume_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    for skill in skills:
        conn.execute("INSERT INTO skills (resume_id, skill) VALUES (?,?)", (resume_id, skill))
    for rec in recs_clean:
        conn.execute(
            "INSERT INTO recommendations (resume_id, career, match_percentage, missing_skills) VALUES (?,?,?,?)",
            (resume_id, rec["career"], rec["match_percentage"], json.dumps(rec["missing_skills"]))
        )
    conn.commit()
    conn.close()

    session["skills"]          = skills
    session["recommendations"] = recs_clean
    session["filename"]        = filename

    return redirect(url_for("result"))


@app.route("/result")
@login_required
def result():
    user     = get_current_user()
    profile  = get_profile(session["user_id"])
    initials = get_initials(profile["full_name"] if profile else None, user["username"])

    skills          = session.get("skills", [])
    recommendations = session.get("recommendations", [])
    filename        = session.get("filename", "Unknown")

    if not skills and not recommendations:
        return redirect(url_for("upload"))

    return render_template("result.html",
                           user=user, profile=profile, initials=initials,
                           skills=skills, recommendations=recommendations,
                           filename=filename)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"[APP] Running at http://0.0.0.0:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
