"""
resume_parser.py
----------------
Handles extraction of raw text from uploaded resume files.
Supports PDF and DOCX formats.
"""

import PyPDF2
import docx
import os


def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file using PyPDF2.
    Returns a single string of all text content.
    """
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"[ERROR] PDF parsing failed: {e}")
        text = ""
    return text.strip()


def extract_text_from_docx(file_path):
    """
    Extract text from a DOCX (Word) file using python-docx.
    Reads each paragraph and joins them into one string.
    """
    text = ""
    try:
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"[ERROR] DOCX parsing failed: {e}")
        text = ""
    return text.strip()


def parse_resume(file_path):
    """
    Main entry point. Detects file type and calls
    the appropriate extraction function.
    Returns extracted text or empty string on failure.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        print(f"[ERROR] Unsupported file format: {ext}")
        return ""
