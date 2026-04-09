# StudyLens — AI Exam Notes Generator

Turn years of past papers into focused, board-specific exam notes in seconds.

---

## System Architecture

```
User Browser / CLI
       │
       ▼
┌─────────────────────────────────────────────┐
│              Flask API  (backend/app.py)     │
│  GET  /metadata/grades                      │
│  GET  /metadata/boards?grade=X              │
│  GET  /metadata/subjects?grade=X&board=Y    │
│  POST /generate-notes                       │
│  POST /predict-questions                    │
└──────────┬──────────────────────────────────┘
           │
    ┌──────▼──────┐
    │ Data Loader │  Reads past_papers/Grade/Board/Subject/
    └──────┬──────┘
           │  PDF or TXT files
    ┌──────▼──────────┐
    │  OCR Pipeline   │  pdfplumber → Tesseract fallback
    └──────┬──────────┘
           │  raw text
    ┌──────▼──────────┐
    │  Text Cleaner   │  strips headers, noise, normalises unicode
    └──────┬──────────┘
           │  clean text
    ┌──────▼──────────────┐
    │  Question Extractor │  MCQ / SHORT / LONG classification
    └──────┬──────────────┘
           │  question list
    ┌──────▼──────────────┐
    │  Topic Analyzer     │  keyword tagging, frequency scoring
    └──────┬──────────────┘
           │  ranked topics
    ┌──────┴──────────────┐
    │                     │
┌───▼────────────┐  ┌─────▼────────────────┐
│ Notes Generator│  │  Prediction Engine   │
│ (OpenAI / rule)│  │  (frequency + recency│
│                │  │   + overdue logic)   │
└────────────────┘  └──────────────────────┘
```

---

## Full Folder Structure

```
studylens/
│
├── backend/
│   ├── app.py                    ← Flask app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── notes.py              ← POST /generate-notes
│   │   ├── predict.py            ← POST /predict-questions
│   │   └── metadata.py           ← GET  /metadata/*
│   └── utils/
│       ├── data_loader.py        ← loads paper files by grade/board/subject
│       ├── ocr_pipeline.py       ← pdfplumber + Tesseract OCR
│       ├── text_cleaner.py       ← removes noise, normalises text
│       ├── question_extractor.py ← classifies MCQ / SHORT / LONG
│       ├── topic_analyzer.py     ← keyword tagging + frequency scoring
│       ├── notes_generator.py    ← OpenAI GPT-4o-mini + fallback
│       └── prediction_engine.py  ← topic predictions + likely questions
│
├── frontend/
│   ├── templates/
│   │   └── index.html            ← single-page UI
│   └── static/
│       ├── style.css
│       └── script.js
│
├── data/
│   └── past_papers/              ← ADD YOUR PAPERS HERE
│       ├── Grade9/
│       ├── Grade10/
│       ├── Grade11/
│       └── Grade12/
│           ├── Federal Board/
│           │   ├── Physics/
│           │   │   ├── 2021.pdf
│           │   │   ├── 2022.pdf
│           │   │   └── 2023.pdf
│           │   ├── Chemistry/
│           │   └── Mathematics/
│           ├── Sindh Board/
│           │   ├── Physics/
│           │   └── Chemistry/
│           └── Karachi Board/
│               └── Chemistry/
│
├── scripts/
│   ├── generate_notes_cli.py     ← CLI interface (no browser needed)
│   └── ingest_papers.py          ← pre-extract text from PDFs
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 1. Setup — Step by Step

### Step 1: System packages

```bash
# Ubuntu / Debian / GitHub Codespaces
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils

# macOS
brew install tesseract poppler

# Verify
tesseract --version
pdfinfo --version
```

> `tesseract` is only used as a fallback for scanned PDFs.
> `poppler-utils` is needed by `pdf2image` to render PDF pages as images.
> For digital (non-scanned) PDFs, neither is required — `pdfplumber` handles them directly.

### Step 2: Python dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Environment

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=sk-your-key-here    # optional — fallback works without it
SECRET_KEY=any-long-random-string
PORT=5000
DEBUG=false
```

### Step 4: Add past papers

Place your PDF or TXT files in the folder structure:
```
data/past_papers/Grade12/Federal Board/Physics/2023.pdf
data/past_papers/Grade12/Federal Board/Physics/2022.pdf
data/past_papers/Grade12/Sindh Board/Chemistry/2023.pdf
```

Rules:
- Folder names must match **exactly** (case-insensitive matching is supported)
- File names can be anything: `2023.pdf`, `physics_2022.pdf`, `annual_exam_2021.txt`
- Use a 4-digit year somewhere in the filename for year tracking: `2023`, `2022`, etc.
- Both `.pdf` and `.txt` formats are supported

### Step 5: (Optional) Pre-extract text from PDFs

This speeds up the app by caching extracted text as `.txt` files next to each PDF:

```bash
python scripts/ingest_papers.py
```

To re-extract (force overwrite):
```bash
python scripts/ingest_papers.py --force
```

### Step 6: Create demo papers (if you have no PDFs yet)

```bash
python scripts/ingest_papers.py --demo
```

This creates sample papers for:
- Grade12 / Federal Board / Physics (2021, 2022, 2023)
- Grade12 / Sindh Board / Physics (2022)
- Grade12 / Karachi Board / Chemistry (2022)

### Step 7: Run the app

```bash
python backend/app.py
```

Open your browser at: **http://localhost:5000**

---

## 2. How to Use the App

### Web Interface

1. Open `http://localhost:5000`
2. Select **Grade** from the first dropdown (auto-populated from your files)
3. Select **Board** (Federal Board, Sindh Board, etc.)
4. Select **Subject** (Physics, Chemistry, etc.)
5. Click **Generate Notes** → get AI-powered exam notes
6. Click **Predict Questions** → see most likely exam topics and questions
7. Use the **Print** button to print or save as PDF

### What the notes contain

| Section | Content |
|---------|---------|
| Overview | 2-3 sentence summary of what the board emphasises |
| Key Topics | Top topics ranked by frequency with importance tags and notes |
| Definitions | Key terms extracted from past papers |
| Exam Tips | Board-specific strategy tips |
| Board-Specific Notes | Patterns unique to the selected board |

### What predictions contain

| Section | Content |
|---------|---------|
| Most Likely Questions | Top 5 actual questions likely to repeat |
| Topic Predictions | Ranked topics with probability (Very High / High / Medium) and reasoning |

---

## 3. CLI Usage (No Browser)

```bash
# Generate notes
python scripts/generate_notes_cli.py \
  --grade Grade12 \
  --board "Federal Board" \
  --subject Physics

# Predict likely questions
python scripts/generate_notes_cli.py \
  --grade Grade12 \
  --board "Federal Board" \
  --subject Physics \
  --predict

# List all available papers
python scripts/generate_notes_cli.py --list
```

---

## 4. API Endpoints

### POST /generate-notes

**Request:**
```json
{
  "grade":   "Grade12",
  "board":   "Federal Board",
  "subject": "Physics"
}
```

**Response:**
```json
{
  "grade": "Grade12",
  "board": "Federal Board",
  "subject": "Physics",
  "papers_found": 3,
  "years_found": ["2021", "2022", "2023"],
  "total_questions_extracted": 87,
  "notes": {
    "summary": "Federal Board Physics XII emphasises...",
    "key_topics": [
      {
        "topic": "Electrostatics",
        "importance": "High",
        "notes": "• Coulomb's Law appears every year...",
        "likely_question_type": "LONG"
      }
    ],
    "definitions": ["Electric Field: ..."],
    "exam_tips": ["Start with Coulomb's Law..."],
    "board_specific_notes": "Federal Board tends to...",
    "fallback": false
  }
}
```

### POST /predict-questions

**Request:**
```json
{
  "grade":   "Grade12",
  "board":   "Federal Board",
  "subject": "Physics",
  "top_n":   10
}
```

**Response:**
```json
{
  "papers_analysed": 3,
  "predictions": [
    {
      "topic":       "Electrostatics",
      "probability": "Very High",
      "reason":      "Appeared in 3 year(s): 2021, 2022, 2023. Appeared in the last 1-2 years.",
      "sample_questions": ["Explain Coulomb's law..."]
    }
  ],
  "most_likely_questions": [
    "Derive the expression for electric field intensity due to a point charge...",
    "Explain Faraday's law of electromagnetic induction..."
  ]
}
```

### GET /metadata

Returns the full tree of available grades → boards → subjects:
```json
{
  "Grade12": {
    "Federal Board": ["Chemistry", "Mathematics", "Physics"],
    "Sindh Board":   ["Chemistry", "Physics"]
  }
}
```

---

## 5. Sample Output

### Notes (CLI)

```
StudyLens — AI Exam Notes
══════════════════════════════════════════════════════════
  Grade:   Grade12
  Board:   Federal Board
  Subject: Physics
══════════════════════════════════════════════════════════

📌 Overview
──────────────────────────────────────────────────────────
Federal Board Physics XII consistently tests Electrostatics,
Electromagnetic Induction, and Modern Physics. Long questions
worth 5 marks appear on these topics every year.

🎯 Key Topics
──────────────────────────────────────────────────────────

  Electrostatics  [High]  [LONG]
  • Coulomb's Law derivation (appeared all 3 years)
  • Electric field intensity and electric flux
  • Gauss's Law — derive and apply to line/plane charges
  • Capacitors — derivation of capacitance, energy stored
  • Dielectric materials and their effect on capacitance

  Electromagnetic Induction  [High]  [LONG]
  • Faraday's and Lenz's laws — state, derive, apply
  • AC Generator — construction, working, diagram
  • Transformer — turns ratio derivation, efficiency
  • Self and mutual inductance with units

📖 Key Definitions
──────────────────────────────────────────────────────────
  • Electric Field Intensity: Force per unit positive charge at a point
  • Capacitance: Ratio of charge stored to potential difference
  • Electromagnetic Induction: Production of EMF by changing magnetic flux

✏️ Exam Tips
──────────────────────────────────────────────────────────
  → Start with the long question you know best — attempt 5, so choose wisely.
  → Draw clear, labelled diagrams for LONG questions — marks are awarded for diagrams.
  → For Federal Board: derivations must show all steps. Skipping steps loses marks.
  → Memorise SI units — MCQs frequently test units.
```

---

## 6. Scalability Plan

### Adding a new board

1. Create the folder:
   ```
   data/past_papers/Grade12/AJK Board/Physics/
   ```
2. Drop PDF files inside
3. The board appears automatically in the app — no code changes needed

### Adding a new subject

1. Create the folder:
   ```
   data/past_papers/Grade12/Federal Board/Biology/
   ```
2. Add topic keywords for Biology in `backend/utils/topic_analyzer.py`:
   ```python
   "Cell Biology": ["cell", "membrane", "mitosis", ...],
   "Genetics":     ["dna", "rna", "mendel", ...],
   ```
3. Drop papers in — subject appears automatically

### Adding more grades

1. Create `data/past_papers/Grade11/Federal Board/Physics/`
2. Add papers — appears automatically

### Improving predictions with more data

The prediction engine scores = frequency × type weight × recency boost.
- **More years** → more accurate frequency counts
- **Marking schemes** → add separate `marking_scheme/` subfolder and cross-reference
- **Embeddings** (future) → replace keyword matching with FAISS vector search for semantic topic grouping

### Upgrading to vector search (advanced)

Replace `topic_analyzer.py`'s keyword matching with:
```python
from sentence_transformers import SentenceTransformer
import faiss

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode([q["text"] for q in questions])
# Build FAISS index, cluster questions into topics
```
This handles topics without predefined keywords and works across languages.

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| `TesseractNotFoundError` | `sudo apt-get install -y tesseract-ocr` |
| `poppler not found` | `sudo apt-get install -y poppler-utils` |
| `OPENAI_API_KEY not set` | Add key to `.env` or use fallback (notes still work) |
| `httpx proxies error` | `pip install httpx==0.27.2` |
| Grade/Board/Subject not showing | Check folder names match the exact path structure |
| Empty notes | Your PDF may be scanned — ensure Tesseract is installed |
| `No papers found` | Run `python scripts/ingest_papers.py --demo` to create test data |

---

## 8. Running in GitHub Codespaces

```bash
# 1. Open repo in Codespaces
# 2. In terminal:
sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils
pip install -r requirements.txt
python scripts/ingest_papers.py --demo   # create sample data
cp .env.example .env                     # configure (add OpenAI key if you have one)
python backend/app.py                    # start server

# Codespaces auto-forwards port 5000 → click the URL in the terminal
```
