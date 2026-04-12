/**
 * static/script.js — StudyLens Notes Generator
 * Handles: cascading dropdowns, API calls, results rendering, and feedback.
 */
"use strict";

/* ── DOM refs ──────────────────────────────────────────────────────────────── */
const gradeSelect   = document.getElementById("grade-select");
const boardSelect   = document.getElementById("board-select");
const subjectSelect = document.getElementById("subject-select");
const generateBtn   = document.getElementById("generate-btn");
const predictBtn    = document.getElementById("predict-btn");
const selectorError = document.getElementById("selector-error");
const loadingBox    = document.getElementById("loading-box");
const loadingMsg    = document.getElementById("loading-msg");

const notesSection  = document.getElementById("notes-results");
const notesMeta     = document.getElementById("notes-meta");
const fallbackAlert = document.getElementById("fallback-alert");
const summaryText   = document.getElementById("summary-text");
const topicsList    = document.getElementById("topics-list");
const defsList      = document.getElementById("defs-list");
const tipsList      = document.getElementById("tips-list");
const boardNoteText = document.getElementById("board-note-text");
const newNotesBtn   = document.getElementById("new-notes-btn");

const predSection   = document.getElementById("predictions");
const predMeta      = document.getElementById("pred-meta");
const likelyList    = document.getElementById("likely-list");
const predList      = document.getElementById("pred-list");
const newPredBtn    = document.getElementById("new-pred-btn");


/* ── Cascading dropdown population ─────────────────────────────────────────── */
async function populateGrades() {
  try {
    const res    = await fetch("/metadata/grades");
    const grades = await res.json();
    gradeSelect.innerHTML = '<option value="">Select grade…</option>';
    grades.forEach(g => {
      const opt = document.createElement("option");
      opt.value = g; opt.textContent = g;
      gradeSelect.appendChild(opt);
    });
  } catch {
    gradeSelect.innerHTML = '<option value="">Error loading grades</option>';
  }
}

async function populateBoards(grade) {
  boardSelect.innerHTML   = '<option value="">Loading…</option>';
  boardSelect.disabled    = true;
  subjectSelect.innerHTML = '<option value="">Select board first</option>';
  subjectSelect.disabled  = true;
  setButtonsEnabled(false);

  try {
    const res    = await fetch(`/metadata/boards?grade=${encodeURIComponent(grade)}`);
    const boards = await res.json();
    boardSelect.innerHTML = '<option value="">Select board…</option>';
    boards.forEach(b => {
      const opt = document.createElement("option");
      opt.value = b; opt.textContent = b;
      boardSelect.appendChild(opt);
    });
    boardSelect.disabled = false;
  } catch {
    boardSelect.innerHTML = '<option value="">Error loading boards</option>';
  }
}

async function populateSubjects(grade, board) {
  subjectSelect.innerHTML = '<option value="">Loading…</option>';
  subjectSelect.disabled  = true;
  setButtonsEnabled(false);

  try {
    const res = await fetch(
      `/metadata/subjects?grade=${encodeURIComponent(grade)}&board=${encodeURIComponent(board)}`
    );
    const subjects = await res.json();
    subjectSelect.innerHTML = '<option value="">Select subject…</option>';
    subjects.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s; opt.textContent = s;
      subjectSelect.appendChild(opt);
    });
    subjectSelect.disabled = false;
  } catch {
    subjectSelect.innerHTML = '<option value="">Error loading subjects</option>';
  }
}

function setButtonsEnabled(enabled) {
  generateBtn.disabled = !enabled;
  predictBtn.disabled  = !enabled;
}

/* ── Change listeners ──────────────────────────────────────────────────────── */
gradeSelect.addEventListener("change", () => {
  if (gradeSelect.value) populateBoards(gradeSelect.value);
});

boardSelect.addEventListener("change", () => {
  if (boardSelect.value && gradeSelect.value) {
    populateSubjects(gradeSelect.value, boardSelect.value);
  }
});

subjectSelect.addEventListener("change", () => {
  setButtonsEnabled(!!subjectSelect.value);
});

/* ── Helpers ────────────────────────────────────────────────────────────────── */
function showError(msg) {
  selectorError.textContent = msg;
  selectorError.hidden = false;
}
function hideError() { selectorError.hidden = true; }

function showLoading(msg) {
  loadingMsg.textContent = msg;
  loadingBox.hidden = false;
  notesSection.hidden = true;
  predSection.hidden  = true;
  document.getElementById("selector").hidden = true;
}
function hideLoading() {
  loadingBox.hidden = true;
}
function resetView() {
  notesSection.hidden = true;
  predSection.hidden  = true;
  hideFeedback();
  document.getElementById("selector").hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* ── Feedback (Task 7) ───────────────────────────────────────────────────────
 * Shows 👍 / 👎 buttons after notes or predictions are rendered.
 * Sends POST /submit-feedback with { feedback: "yes" | "no" }.
 * ─────────────────────────────────────────────────────────────────────────── */

/**
 * Build and inject the feedback bar into the given parent element.
 * @param {HTMLElement} parentEl - element to append the bar into
 */
function injectFeedbackBar(parentEl) {
  // Remove any previously injected bar to avoid duplicates
  hideFeedback();

  const bar = document.createElement("div");
  bar.id = "feedback-bar";
  bar.style.cssText = [
    "display:flex",
    "align-items:center",
    "gap:12px",
    "padding:14px 18px",
    "background:var(--surface)",
    "border:1px solid var(--border)",
    "border-radius:var(--r-sm)",
    "margin-top:4px",
  ].join(";");

  bar.innerHTML = `
    <span style="font-size:13px;color:var(--subtle);flex:1;">
      Were these notes helpful?
    </span>
    <button
      id="feedback-yes"
      style="
        background:var(--surface-2);border:1px solid var(--border);
        color:var(--text);padding:7px 16px;border-radius:var(--r-sm);
        font-family:var(--font);font-size:13px;cursor:pointer;
        transition:border-color 0.18s ease,color 0.18s ease;
      "
      title="Helpful"
    >👍 Helpful</button>
    <button
      id="feedback-no"
      style="
        background:var(--surface-2);border:1px solid var(--border);
        color:var(--text);padding:7px 16px;border-radius:var(--r-sm);
        font-family:var(--font);font-size:13px;cursor:pointer;
        transition:border-color 0.18s ease,color 0.18s ease;
      "
      title="Not helpful"
    >👎 Not Helpful</button>
    <span id="feedback-thanks" style="font-size:13px;color:var(--green);display:none;">
      ✓ Thanks for your feedback!
    </span>
  `;

  parentEl.appendChild(bar);

  // Wire up click handlers
  document.getElementById("feedback-yes").addEventListener("click", () => submitFeedback("yes"));
  document.getElementById("feedback-no").addEventListener("click",  () => submitFeedback("no"));
}

/** Remove the feedback bar if it exists. */
function hideFeedback() {
  const bar = document.getElementById("feedback-bar");
  if (bar) bar.remove();
}

/**
 * Send feedback to the server.
 * @param {"yes"|"no"} value
 */
async function submitFeedback(value) {
  const yesBtn    = document.getElementById("feedback-yes");
  const noBtn     = document.getElementById("feedback-no");
  const thanksMsg = document.getElementById("feedback-thanks");

  // Disable buttons immediately to prevent double-submit
  if (yesBtn) yesBtn.disabled = true;
  if (noBtn)  noBtn.disabled  = true;

  try {
    const res = await fetch("/submit-feedback", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ feedback: value }),
    });

    if (res.ok) {
      // Hide buttons, show thank-you message
      if (yesBtn)    yesBtn.style.display    = "none";
      if (noBtn)     noBtn.style.display     = "none";
      if (thanksMsg) thanksMsg.style.display = "inline";
    } else {
      // Re-enable on failure so user can retry
      if (yesBtn) yesBtn.disabled = false;
      if (noBtn)  noBtn.disabled  = false;
      console.warn("Feedback submission failed:", res.status);
    }
  } catch (err) {
    // Network error — re-enable silently
    if (yesBtn) yesBtn.disabled = false;
    if (noBtn)  noBtn.disabled  = false;
    console.warn("Feedback network error:", err);
  }
}

/* ── Notes rendering ────────────────────────────────────────────────────────── */
function renderNotes(data) {
  const n = data.notes;

  // Meta bar
  notesMeta.textContent = [
    `${data.grade} · ${data.board} · ${data.subject}`,
    `${data.papers_found} paper(s) analysed`,
    data.years_found?.length ? `Years: ${data.years_found.join(", ")}` : "",
    `${data.total_questions_extracted || 0} questions extracted`,
  ].filter(Boolean).join("  ·  ");

  // Fallback warning
  fallbackAlert.hidden = !n.fallback;

  // Summary
  summaryText.textContent = n.summary || "";

  // Key topics
  topicsList.innerHTML = "";
  (n.key_topics || []).forEach(t => {
    const impBadge  = t.importance === "High" ? "badge-high" : "badge-medium";
    const typeBadge = t.likely_question_type === "LONG"  ? "badge-long"
                    : t.likely_question_type === "SHORT" ? "badge-short"
                    : "badge-mcq";
    topicsList.innerHTML += `
      <div class="topic-item">
        <div class="topic-header">
          <span class="topic-name">${esc(t.topic)}</span>
          <span class="badge ${impBadge}">${esc(t.importance)}</span>
          <span class="badge ${typeBadge}">${esc(t.likely_question_type)}</span>
        </div>
        <div class="topic-notes">${esc(t.notes)}</div>
      </div>`;
  });

  // Definitions
  defsList.innerHTML = "";
  (n.definitions || []).forEach(def => {
    const colon = def.indexOf(":");
    const term  = colon > -1 ? def.slice(0, colon).trim() : "Definition";
    const desc  = colon > -1 ? def.slice(colon + 1).trim() : def;
    defsList.innerHTML += `
      <li>
        <div class="def-term">${esc(term)}</div>
        ${esc(desc)}
      </li>`;
  });

  // Exam tips
  tipsList.innerHTML = "";
  (n.exam_tips || []).forEach(tip => {
    tipsList.innerHTML += `<li>${esc(tip)}</li>`;
  });

  // Board-specific
  boardNoteText.textContent = n.board_specific_notes || "";

  hideLoading();
  notesSection.hidden = false;
  notesSection.scrollIntoView({ behavior: "smooth" });

  // Task 7 — inject feedback bar at the bottom of the notes section
  injectFeedbackBar(notesSection);
}

/* ── Predictions rendering ───────────────────────────────────────────────────── */
function renderPredictions(data) {
  predMeta.textContent = [
    `${data.grade} · ${data.board} · ${data.subject}`,
    `${data.papers_analysed} paper(s) analysed`,
  ].join("  ·  ");

  // Likely questions
  likelyList.innerHTML = "";
  (data.most_likely_questions || []).forEach(q => {
    likelyList.innerHTML += `<li>${esc(q)}</li>`;
  });
  if (!data.most_likely_questions?.length) {
    likelyList.innerHTML = "<li>No questions predicted — add more past papers.</li>";
  }

  // Topic predictions
  predList.innerHTML = "";
  (data.predictions || []).forEach(p => {
    const probClass = p.probability === "Very High" ? "badge-very-high"
                    : p.probability === "High"      ? "badge-high-pred"
                    : "badge-medium-pred";

    const samplesHtml = p.sample_questions?.length
      ? `<div class="pred-samples">
           ${p.sample_questions.map(s => `<p>• ${esc(s.slice(0, 200))}</p>`).join("")}
         </div>`
      : "";

    predList.innerHTML += `
      <div class="pred-item">
        <div class="pred-header">
          <span class="pred-topic">${esc(p.topic)}</span>
          <span class="badge ${probClass}">${esc(p.probability)}</span>
        </div>
        <p class="pred-reason">${esc(p.reason)}</p>
        ${samplesHtml}
      </div>`;
  });

  hideLoading();
  predSection.hidden = false;
  predSection.scrollIntoView({ behavior: "smooth" });

  // Task 7 — inject feedback bar at the bottom of the predictions section
  injectFeedbackBar(predSection);
}

/* ── Button handlers ─────────────────────────────────────────────────────────── */
generateBtn.addEventListener("click", async () => {
  hideError();
  const grade   = gradeSelect.value;
  const board   = boardSelect.value;
  const subject = subjectSelect.value;
  if (!grade || !board || !subject) { showError("Please select grade, board, and subject."); return; }

  showLoading("Analysing past papers and generating notes…");

  try {
    const res  = await fetch("/generate-notes", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ grade, board, subject }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `Server error ${res.status}`);
    renderNotes(data);
  } catch (e) {
    hideLoading();
    document.getElementById("selector").hidden = false;
    showError("Error: " + e.message);
  }
});

predictBtn.addEventListener("click", async () => {
  hideError();
  const grade   = gradeSelect.value;
  const board   = boardSelect.value;
  const subject = subjectSelect.value;
  if (!grade || !board || !subject) { showError("Please select grade, board, and subject."); return; }

  showLoading("Predicting likely exam questions…");

  try {
    const res  = await fetch("/predict-questions", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ grade, board, subject, top_n: 10 }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `Server error ${res.status}`);
    renderPredictions(data);
  } catch (e) {
    hideLoading();
    document.getElementById("selector").hidden = false;
    showError("Error: " + e.message);
  }
});

newNotesBtn.addEventListener("click", resetView);
newPredBtn.addEventListener("click",  resetView);

/* ── Init ───────────────────────────────────────────────────────────────────── */
populateGrades();
