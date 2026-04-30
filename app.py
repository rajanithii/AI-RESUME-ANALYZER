"""
app.py — ResumeAI Full Stack (Render-Ready Version)
Includes: Auth (login/register), Profile, Resume Analysis Dashboard
"""

import os, sqlite3, json, hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename

# Import your custom logic
try:
    from project2.utils.resume_parser import parse_resume
    from project2.utils.skill_extractor import extract_skills
    from project2.utils.recommender import recommend_careers
except ImportError:
    from utils.resume_parser import parse_resume
    from utils.skill_extractor import extract_skills
    from utils.recommender import recommend_careers

# NLTK downloads - Essential for Render deployment
import nltk
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# --- CONFIGURATION ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Adjusting paths to match your 'project2' subfolder structure
app = Flask(__name__,
            template_folder='project2/templates',
            static_folder='project2/static')

app.secret_key = "resumeai_ultra_secret_2024_xK9p"

ALLOWED_EXTENSIONS = {"pdf", "docx"}
UPLOAD_FOLDER = os.path.join(BASE_DIR, "project2", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Use absolute path for database
DATABASE = os.path.join(BASE_DIR, "database.db")

# ══════════════════════════════════════════════════════
#  DATABASE SETUP
# ══════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
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
    # Profile table
    c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT, phone TEXT, location TEXT, dob TEXT, gender TEXT,
            linkedin TEXT, github TEXT, bio TEXT, degree TEXT, college TEXT,
            graduation_year TEXT, job_title TEXT, experience_years TEXT,
            avatar_color TEXT DEFAULT '#6EE7F7', updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Resumes, Skills, Recommendations tables
    c.execute("CREATE TABLE IF NOT EXISTS resumes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT NOT NULL, upload_time TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id))")
    c.execute("CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY AUTOINCREMENT, resume_id INTEGER, skill TEXT NOT NULL, FOREIGN KEY (resume_id) REFERENCES resumes(id))")
    c.execute("CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY AUTOINCREMENT, resume_id INTEGER, career TEXT NOT NULL, match_percentage REAL, missing_skills TEXT, FOREIGN KEY (resume_id) REFERENCES resumes(id))")
    conn.commit()
    conn.close()
    print("[DB] Initialized successfully.")

# CRITICAL: Initialize DB outside the _main_ block for Render/Gunicorn
init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
