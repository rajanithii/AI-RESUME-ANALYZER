"""
recommender.py
--------------
Career Recommendation Engine.
Maps careers to required skills and computes match scores.
"""

# ─────────────────────────────────────────────────────────────
#  Career → Required Skills Mapping
#  Each career has a set of skills needed to qualify.
# ─────────────────────────────────────────────────────────────
CAREER_SKILLS = {
    "Data Scientist": {
        "Python", "Machine Learning", "Statistics", "SQL",
        "Pandas", "NumPy", "Data Analysis", "Matplotlib",
        "scikit-learn", "Deep Learning"
    },
    "Machine Learning Engineer": {
        "Python", "Machine Learning", "Deep Learning", "TensorFlow",
        "PyTorch", "scikit-learn", "Docker", "Git", "API"
    },
    "AI Engineer": {
        "Python", "Deep Learning", "NLP", "TensorFlow", "PyTorch",
        "LLM", "Generative AI", "Transformers", "Docker"
    },
    "Web Developer": {
        "HTML", "CSS", "JavaScript", "React", "Node.js",
        "REST API", "Git", "Bootstrap", "SQL"
    },
    "Frontend Developer": {
        "HTML", "CSS", "JavaScript", "React", "Angular",
        "Vue", "TypeScript", "Bootstrap", "Git"
    },
    "Backend Developer": {
        "Python", "Node.js", "SQL", "PostgreSQL", "MongoDB",
        "REST API", "Docker", "Git", "Django", "Flask"
    },
    "Software Engineer": {
        "Python", "Java", "C++", "Algorithms", "Data Structures",
        "OOP", "Git", "SQL", "Problem Solving"
    },
    "Data Analyst": {
        "SQL", "Python", "Excel", "Data Analysis", "Data Visualization",
        "Tableau", "Power BI", "Statistics", "Pandas"
    },
    "Cybersecurity Analyst": {
        "Cybersecurity", "Network Security", "Ethical Hacking",
        "Linux", "Python", "Cryptography", "Firewalls", "SIEM"
    },
    "DevOps Engineer": {
        "Docker", "Kubernetes", "AWS", "CI/CD", "Linux",
        "Git", "Python", "Terraform", "Bash"
    },
    "Cloud Engineer": {
        "AWS", "Azure", "GCP", "Docker", "Kubernetes",
        "Linux", "Python", "Terraform", "CI/CD"
    },
    "Mobile Developer": {
        "Mobile Development", "Android", "iOS", "Java",
        "Swift", "Kotlin", "React", "Git"
    },
}


def recommend_careers(detected_skills, top_n=5):
    """
    Compare detected skills against each career's requirements.
    Returns top N career matches with:
      - match_percentage
      - matched_skills
      - missing_skills
    Sorted by best match first.
    """
    detected_set = set(detected_skills)
    results = []

    for career, required_skills in CAREER_SKILLS.items():
        matched = detected_set & required_skills          # Skills user HAS
        missing = required_skills - detected_set          # Skills user LACKS

        # Calculate percentage match
        if len(required_skills) == 0:
            percentage = 0
        else:
            percentage = round((len(matched) / len(required_skills)) * 100, 1)

        results.append({
            "career": career,
            "match_percentage": percentage,
            "matched_skills": sorted(list(matched)),
            "missing_skills": sorted(list(missing)),
            "total_required": len(required_skills),
            "total_matched": len(matched),
        })

    # Sort by match percentage descending
    results.sort(key=lambda x: x["match_percentage"], reverse=True)

    # Return top N results (only those with at least 1 match)
    top = [r for r in results if r["total_matched"] > 0]
    return top[:top_n]
