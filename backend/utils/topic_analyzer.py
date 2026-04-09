"""
backend/utils/topic_analyzer.py
Detects topics in questions, counts frequency across years,
and ranks them by exam importance.

Approach:
  - A lightweight keyword-to-topic mapping covers the most common
    Pakistani board subjects without needing a heavy NLP library.
  - Unknown topics fall into "General / Other".
  - Frequency = how many distinct years a topic appeared in.
  - Importance score = frequency weighted by question type marks.
"""

import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


# ── Topic → Keywords mapping ──────────────────────────────────────────────────
# Extend this dict to cover more subjects / boards.
# Keys are canonical topic names; values are keyword lists (case-insensitive).

TOPIC_KEYWORDS: dict[str, list[str]] = {
    # Physics
    "Kinematics":            ["velocity", "acceleration", "displacement", "projectile", "motion", "kinematics"],
    "Newton's Laws":         ["newton", "force", "inertia", "momentum", "friction"],
    "Work, Energy & Power":  ["work", "energy", "power", "kinetic", "potential", "conservation of energy"],
    "Waves & Oscillations":  ["wave", "oscillat", "frequency", "amplitude", "simple harmonic", "pendulum"],
    "Thermodynamics":        ["heat", "temperature", "thermodynamics", "entropy", "carnot", "specific heat"],
    "Electrostatics":        ["electric field", "coulomb", "capacitor", "charge", "potential difference"],
    "Current Electricity":   ["ohm", "resistance", "current", "circuit", "kirchhoff", "volt", "ammeter"],
    "Electromagnetism":      ["magnetic field", "faraday", "electromagnetic", "lenz", "induced", "flux"],
    "Modern Physics":        ["photoelectric", "quantum", "photon", "nuclear", "radioactive", "half life"],
    "Optics":                ["refraction", "reflection", "lens", "mirror", "light", "snell"],
    # Chemistry
    "Atomic Structure":      ["atom", "proton", "neutron", "electron", "orbit", "quantum number", "atomic structure"],
    "Chemical Bonding":      ["bond", "ionic", "covalent", "hybridization", "electronegativity"],
    "Acids & Bases":         ["acid", "base", "ph", "buffer", "neutralization", "titration"],
    "Electrochemistry":      ["electrolysis", "electrode", "cell", "oxidation", "reduction", "redox"],
    "Organic Chemistry":     ["alkane", "alkene", "alkyne", "benzene", "organic", "hydrocarbon", "functional group"],
    "Chemical Equilibrium":  ["equilibrium", "le chatelier", "kc", "kp", "reversible"],
    "Thermochemistry":       ["enthalpy", "exothermic", "endothermic", "hess", "bond energy"],
    "Reaction Kinetics":     ["rate of reaction", "activation energy", "catalyst", "kinetics"],
    # Mathematics
    "Algebra":               ["algebra", "polynomial", "quadratic", "factor", "equation", "simultaneous"],
    "Trigonometry":          ["sin", "cos", "tan", "trigonometry", "angle", "identity", "triangle"],
    "Calculus":              ["derivative", "integral", "limit", "differentiation", "integration", "calculus"],
    "Matrices":              ["matrix", "matrices", "determinant", "inverse", "eigenvalue"],
    "Statistics":            ["mean", "median", "mode", "variance", "standard deviation", "probability"],
    "Coordinate Geometry":   ["parabola", "ellipse", "hyperbola", "circle", "conic", "locus"],
    "Sequences & Series":    ["sequence", "series", "arithmetic progression", "geometric progression", "ap", "gp"],
    # Biology
    "Cell Biology":          ["cell", "membrane", "organelle", "mitosis", "meiosis", "nucleus"],
    "Genetics":              ["gene", "dna", "rna", "heredity", "mendel", "chromosome", "mutation"],
    "Ecology":               ["ecosystem", "food chain", "biome", "ecology", "habitat", "population"],
    "Human Physiology":      ["digestion", "respiration", "circulation", "nervous system", "kidney", "heart"],
    "Plant Biology":         ["photosynthesis", "transpiration", "chlorophyll", "root", "stem", "leaf"],
}


def _tokenize(text: str) -> str:
    """Lowercase and normalise text for keyword matching."""
    return text.lower()


def tag_topic(question_text: str) -> str:
    """
    Return the best-matching topic for a question.
    Falls back to 'General / Other' if no keyword matches.
    """
    lower = _tokenize(question_text)
    best_topic = "General / Other"
    best_count = 0

    for topic, keywords in TOPIC_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in lower)
        if count > best_count:
            best_count = count
            best_topic = topic

    return best_topic


def analyse_topics(questions: list[dict]) -> dict:
    """
    Analyse topic frequency and importance from a list of extracted questions.

    Args:
        questions: Output of question_extractor.extract_from_papers()

    Returns:
        {
          "topic_frequency": { topic: int },     # times topic appeared
          "topic_years":     { topic: [years] }, # which years it appeared
          "topic_types":     { topic: {MCQ:n, SHORT:n, LONG:n} },
          "ranked_topics":   [ { topic, frequency, years, score } ]
        }
    """
    topic_freq  = defaultdict(int)
    topic_years = defaultdict(set)
    topic_types = defaultdict(lambda: defaultdict(int))

    type_weights = {"LONG": 5, "SHORT": 2, "MCQ": 1}

    for q in questions:
        topic = tag_topic(q["text"])
        q["topic"] = topic          # mutate in place so callers get topic too

        q_type = q.get("type", "SHORT")
        year   = q.get("year") or "Unknown"

        topic_freq[topic]              += 1
        topic_years[topic].add(year)
        topic_types[topic][q_type]     += 1

    # Build importance score: freq × avg_weight
    ranked = []
    for topic, freq in topic_freq.items():
        types   = topic_types[topic]
        total_w = sum(types[t] * type_weights.get(t, 1) for t in types)
        n_qs    = sum(types.values())
        score   = round(freq * (total_w / max(n_qs, 1)), 2)
        ranked.append({
            "topic":     topic,
            "frequency": freq,
            "years":     sorted(topic_years[topic]),
            "types":     dict(types),
            "score":     score,
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "topic_frequency": dict(topic_freq),
        "topic_years":     {k: sorted(v) for k, v in topic_years.items()},
        "topic_types":     {k: dict(v)   for k, v in topic_types.items()},
        "ranked_topics":   ranked,
    }
