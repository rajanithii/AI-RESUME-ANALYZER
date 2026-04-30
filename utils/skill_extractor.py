"""
skill_extractor.py
------------------
Uses HYBRID approach for skill detection:
  1. Keyword Matching  — fast, reliable for known tech terms
  2. TextBlob NLP      — noun-phrase extraction for unknown skills

This hybrid approach is stronger than either alone.
"""

try:
    from textblob import TextBlob
    nlp_available = True
except ImportError:
    print("[WARNING] TextBlob not available. Using keyword matching only.")
    nlp_available = False

# SKILL_KEYWORDS remains the same


# ─────────────────────────────────────────────
#  Master skill keyword list (case-insensitive)
# ─────────────────────────────────────────────
SKILL_KEYWORDS = {
    # Programming Languages
    "Python", "Java", "C++", "C", "C#", "R", "Go", "Rust", "Swift",
    "Kotlin", "PHP", "Ruby", "Scala", "TypeScript", "Bash", "MATLAB",

    # Web Development
    "HTML", "CSS", "JavaScript", "React", "Angular", "Vue", "Node.js",
    "Django", "Flask", "Bootstrap", "jQuery", "REST API", "GraphQL",
    "Next.js", "Express", "FastAPI", "Tailwind",

    # Data & AI
    "Machine Learning", "Deep Learning", "NLP", "Natural Language Processing",
    "Computer Vision", "TensorFlow", "PyTorch", "Keras", "scikit-learn",
    "Pandas", "NumPy", "Matplotlib", "Seaborn", "OpenCV", "Hugging Face",
    "LLM", "Generative AI", "Transformers",

    # Data & Databases
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Redis",
    "Data Analysis", "Data Science", "Big Data", "Hadoop", "Spark",
    "Power BI", "Tableau", "Excel", "Data Visualization",

    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes",
    "CI/CD", "Git", "GitHub", "Linux", "DevOps", "Terraform",

    # Security
    "Cybersecurity", "Ethical Hacking", "Penetration Testing",
    "Network Security", "Cryptography", "Firewalls", "SIEM",

    # Soft Skills
    "Communication", "Leadership", "Teamwork", "Problem Solving",
    "Project Management", "Agile", "Scrum", "Critical Thinking",
    "Time Management", "Presentation",

    # Other Technical
    "Statistics", "Mathematics", "Algorithms", "Data Structures",
    "OOP", "Microservices", "API", "Mobile Development", "Android", "iOS",
}

# Normalize to lowercase map for matching
SKILL_MAP = {skill.lower(): skill for skill in SKILL_KEYWORDS}


def extract_skills_by_keywords(text):
    """
    METHOD 1: Keyword Matching
    --------------------------
    Searches the resume text for known skill keywords.
    Case-insensitive, handles multi-word skills like 'Machine Learning'.
    Fast and very accurate for known terms.
    """
    found = set()
    text_lower = text.lower()

    for skill_lower, skill_original in SKILL_MAP.items():
        # Use word-boundary-style matching (check surrounding chars)
        idx = text_lower.find(skill_lower)
        while idx != -1:
            # Check character before and after for word boundary
            before = text_lower[idx - 1] if idx > 0 else " "
            after = text_lower[idx + len(skill_lower)] if idx + len(skill_lower) < len(text_lower) else " "
            if not before.isalpha() and not after.isalpha():
                found.add(skill_original)
            idx = text_lower.find(skill_lower, idx + 1)

    return found


def extract_skills_by_nlp(text):
    """
    METHOD 2: TextBlob NLP Noun-Phrase Extraction
    ---------------------------------------------------
    Uses TextBlob to extract noun phrases from text.
    Then checks if those noun phrases match known skills.
    This catches skills even with slight variations in phrasing.
    """
    if not nlp_available:
        return set()

    found = set()
    blob = TextBlob(text[:10000])  # Limit to avoid memory issues

    # Extract noun phrases
    for np in blob.noun_phrases:
        np_lower = np.lower().strip()
        if np_lower in SKILL_MAP:
            found.add(SKILL_MAP[np_lower])

    return found


def extract_skills(text):
    """
    HYBRID SKILL EXTRACTION
    -----------------------
    Combines keyword matching + NLP for best coverage.
    Returns sorted list of detected skill strings.
    """
    if not text:
        return []

    # Run both methods
    keyword_skills = extract_skills_by_keywords(text)
    nlp_skills = extract_skills_by_nlp(text)

    # Merge results (union of both sets)
    all_skills = keyword_skills | nlp_skills

    return sorted(list(all_skills))
