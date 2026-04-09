#!/usr/bin/env python3
"""
scripts/generate_notes_cli.py
Command-line interface for StudyLens.

Usage:
  python scripts/generate_notes_cli.py --grade Grade12 --board "Federal Board" --subject Physics
  python scripts/generate_notes_cli.py --grade Grade12 --board "Federal Board" --subject Physics --predict
  python scripts/generate_notes_cli.py --list
"""

import sys
import os
import argparse

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv()

from utils.data_loader        import load_all_texts, list_grades, list_boards, list_subjects
from utils.text_cleaner       import clean_papers
from utils.question_extractor import extract_from_papers
from utils.topic_analyzer     import analyse_topics
from utils.notes_generator    import generate_notes
from utils.prediction_engine  import rank_predictions, predict_likely_questions

# ── Colour helpers ────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
GREY   = "\033[90m"
RED    = "\033[91m"


def hr(char="─", width=70):
    print(char * width)


def heading(text: str):
    print(f"\n{BOLD}{YELLOW}{text}{RESET}")
    hr()


def list_available():
    """Print all available grade/board/subject combinations."""
    grades = list_grades()
    if not grades:
        print(f"{RED}No past papers found.{RESET} Add files to data/past_papers/")
        return

    heading("Available Past Papers")
    for g in grades:
        print(f"\n{BOLD}{g}{RESET}")
        for b in list_boards(g):
            subjects = list_subjects(g, b)
            print(f"  {CYAN}{b}{RESET}")
            for s in subjects:
                print(f"    • {s}")


def run_notes(grade: str, board: str, subject: str):
    """Generate and print exam notes."""
    print(f"\n{BOLD}StudyLens — AI Exam Notes{RESET}")
    hr("═")
    print(f"  Grade:   {CYAN}{grade}{RESET}")
    print(f"  Board:   {CYAN}{board}{RESET}")
    print(f"  Subject: {CYAN}{subject}{RESET}")
    hr("═")

    # Pipeline
    print(f"\n{GREY}[1/4] Loading past papers…{RESET}")
    papers = load_all_texts(grade, board, subject)
    if not papers:
        print(f"{RED}No papers found.{RESET} Check folder: data/past_papers/{grade}/{board}/{subject}/")
        return

    print(f"      Found {len(papers)} paper(s): {[p['filename'] for p in papers]}")

    print(f"{GREY}[2/4] Cleaning text…{RESET}")
    cleaned   = clean_papers(papers)

    print(f"{GREY}[3/4] Extracting questions…{RESET}")
    questions = extract_from_papers(cleaned)
    print(f"      Extracted {len(questions)} questions")

    print(f"{GREY}[4/4] Generating notes…{RESET}")
    analysis  = analyse_topics(questions)
    notes     = generate_notes(grade, board, subject, analysis["ranked_topics"], questions)

    if notes.get("fallback"):
        print(f"{YELLOW}⚠ AI unavailable — showing rule-based notes.{RESET}")
        if notes.get("ai_error"):
            print(f"  Reason: {GREY}{notes['ai_error']}{RESET}")

    # Print
    heading("📌 Overview")
    print(notes.get("summary", "—"))

    heading("🎯 Key Topics")
    for t in notes.get("key_topics", []):
        imp   = t.get("importance", "?")
        qtype = t.get("likely_question_type", "?")
        col   = GREEN if imp == "High" else YELLOW
        print(f"\n  {BOLD}{t['topic']}{RESET}  [{col}{imp}{RESET}]  [{GREY}{qtype}{RESET}]")
        print(f"  {t.get('notes', '')}")

    heading("📖 Key Definitions")
    for d in notes.get("definitions", []):
        print(f"  • {d}")

    heading("✏️ Exam Tips")
    for tip in notes.get("exam_tips", []):
        print(f"  → {tip}")

    heading(f"🏛 Board-Specific: {board}")
    print(notes.get("board_specific_notes", "—"))

    hr("═")
    print(f"\n{GREEN}Notes generated successfully.{RESET}")


def run_predictions(grade: str, board: str, subject: str, top_n: int = 10):
    """Run and print the prediction engine."""
    print(f"\n{BOLD}StudyLens — Question Predictions{RESET}")
    hr("═")

    papers    = load_all_texts(grade, board, subject)
    if not papers:
        print(f"{RED}No papers found.{RESET}")
        return

    cleaned   = clean_papers(papers)
    questions = extract_from_papers(cleaned)
    analysis  = analyse_topics(questions)

    predictions     = rank_predictions(analysis["ranked_topics"], questions, top_n=top_n)
    likely_questions = predict_likely_questions(questions, top_n=5)

    heading("🔮 Most Likely Exam Questions")
    for i, q in enumerate(likely_questions, 1):
        print(f"\n  Q{i}. {q[:250]}")

    heading("📊 Topic Predictions")
    for p in predictions:
        prob_col = GREEN if p["probability"] == "Very High" else YELLOW if p["probability"] == "High" else CYAN
        print(f"\n  {BOLD}{p['topic']}{RESET}  — {prob_col}{p['probability']}{RESET}")
        print(f"  {GREY}{p['reason']}{RESET}")
        for s in p.get("sample_questions", [])[:2]:
            print(f"    • {s[:180]}")

    hr("═")
    print(f"\n{GREEN}Predictions complete.{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="StudyLens — AI Exam Notes CLI")
    parser.add_argument("--list",    action="store_true", help="List available papers")
    parser.add_argument("--grade",   type=str, help="e.g. Grade12")
    parser.add_argument("--board",   type=str, help="e.g. 'Federal Board'")
    parser.add_argument("--subject", type=str, help="e.g. Physics")
    parser.add_argument("--predict", action="store_true", help="Run prediction engine")
    parser.add_argument("--top-n",   type=int, default=10, help="Number of predictions")
    args = parser.parse_args()

    if args.list:
        list_available()
        return

    if not args.grade or not args.board or not args.subject:
        parser.print_help()
        sys.exit(1)

    if args.predict:
        run_predictions(args.grade, args.board, args.subject, args.top_n)
    else:
        run_notes(args.grade, args.board, args.subject)


if __name__ == "__main__":
    main()
