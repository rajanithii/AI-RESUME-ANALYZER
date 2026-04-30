import os, sqlite3, json, hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

# 1. FIX: Relative imports for utils since app.py is inside project2
try:
    from utils.resume_parser import parse_resume
    from utils.skill_extractor import extract_skills
    from utils.recommender import recommend_careers
except ImportError:
    # Fallback for different environments
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

# 2. FIX: BASE_DIR and Folder Paths
# Since app.py is INSIDE project2, templates are in the same folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__,
            template_folder='templates', # Corrected: just 'templates'
            static_folder='static')      # Corrected: just 'static'

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
    conn = sqlite3.connect(DATABASE)
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

# Start DB
init_db()

# ... [Keep your hash_password, login_required, and all Routes exactly as they were] ...
# (The rest of your logic was fine!)

if __name__ == "_main_":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
