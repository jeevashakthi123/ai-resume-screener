/**
 * ResumeAI – main.js
 * Handles form submission, drag-and-drop, and results rendering.
 */

// ── Element refs ─────────────────────────────────────────────────────────────
const form        = document.getElementById("screenForm");
const submitBtn   = document.getElementById("submitBtn");
const overlay     = document.getElementById("overlay");
const resultsEl   = document.getElementById("results");
const resultsCount= document.getElementById("resultsCount");
const candidateTable = document.getElementById("candidateTable");
const errorList   = document.getElementById("errorList");
const fileListEl  = document.getElementById("fileList");
const chartContainer = document.getElementById("chartContainer");
const chartImg    = document.getElementById("chartImg");
const resumeInput = document.getElementById("resumes");
const resumeDropzone = document.getElementById("resumeDropzone");
const jdDropzone  = document.getElementById("jdDropzone");

// ── Drag & Drop ──────────────────────────────────────────────────────────────
[jdDropzone, resumeDropzone].forEach(zone => {
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const input = zone.querySelector("input[type=file]");
    if (input) {
      input.files = e.dataTransfer.files;
      input.dispatchEvent(new Event("change"));
    }
  });
});

// ── File list preview ────────────────────────────────────────────────────────
resumeInput.addEventListener("change", () => {
  fileListEl.innerHTML = "";
  Array.from(resumeInput.files).forEach(f => {
    const chip = document.createElement("div");
    chip.className = "file-chip";
    chip.innerHTML = `<span class="fc-icon">📄</span>${f.name}`;
    fileListEl.appendChild(chip);
  });
});

// ── Form submit ──────────────────────────────────────────────────────────────
form.addEventListener("submit", async e => {
  e.preventDefault();

  const jdText   = document.getElementById("job_description").value.trim();
  const jdFile   = document.getElementById("job_desc_file").files[0];
  const resumes  = resumeInput.files;
  const jobTitle = document.getElementById("job_title").value.trim();

  if (!jdText && !jdFile) {
    alert("Please provide a job description (text or file).");
    return;
  }
  if (!resumes || resumes.length === 0) {
    alert("Please upload at least one resume file.");
    return;
  }

  const data = new FormData(form);

  // Show loading
  overlay.classList.remove("hidden");
  submitBtn.disabled = true;
  resultsEl.classList.add("hidden");

  try {
    const resp = await fetch("/screen", { method: "POST", body: data });
    const json = await resp.json();

    if (!resp.ok) {
      throw new Error(json.error || "Server error");
    }

    renderResults(json);
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    overlay.classList.add("hidden");
    submitBtn.disabled = false;
  }
});

// ── Render results ───────────────────────────────────────────────────────────
function renderResults(data) {
  const { candidates = [], chart_url, errors = [], job_title, session_id } = data;

  resultsEl.classList.remove("hidden");
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });

  resultsCount.textContent = `${candidates.length} candidates · Session #${session_id}`;

  // Chart
  if (chart_url) {
    chartImg.src = chart_url + "?t=" + Date.now();
    chartContainer.classList.remove("hidden");
  } else {
    chartContainer.classList.add("hidden");
  }

  // Table
  candidateTable.innerHTML = buildTable(candidates);

  // Errors
  errorList.innerHTML = errors.map(e =>
    `<div class="error-item">⚠ ${e}</div>`
  ).join("");

  // Animate bars
  requestAnimationFrame(() => {
    document.querySelectorAll(".match-bar").forEach(bar => {
      const w = bar.dataset.width;
      bar.style.width = w + "%";
    });
  });
}

function buildTable(candidates) {
  if (!candidates.length) return "<p style='color:var(--text-muted)'>No candidates to display.</p>";

  const rows = candidates.map(c => {
    const tierClass = c.tier ? c.tier.toLowerCase() : "low";
    const kws = (c.matched_keywords || []).slice(0, 8)
      .map(k => `<span class="kw-chip">${k}</span>`).join("");
    const kwMore = c.matched_keywords && c.matched_keywords.length > 8
      ? `<span class="kw-more">+${c.matched_keywords.length - 8}</span>` : "";

    return `
      <tr>
        <td class="rank-cell">${c.rank}</td>
        <td class="name-cell">${escHtml(c.name)}</td>
        <td class="score-cell">${(+c.score).toFixed(4)}</td>
        <td>
          <div class="match-bar-wrap">
            <div class="match-bar" data-width="${c.match_pct}" style="width:0%"></div>
            <span class="match-label">${c.match_pct}%</span>
          </div>
        </td>
        <td><span class="tier-badge tier-${tierClass}">${c.tier}</span></td>
        <td class="kw-cell">${kws}${kwMore || (!kws ? "<span style='color:var(--text-dim)'>–</span>" : "")}</td>
      </tr>`;
  }).join("");

  return `
    <div class="table-wrap">
      <table class="cand-table">
        <thead>
          <tr>
            <th>#</th><th>Name</th><th>Score</th>
            <th>Match %</th><th>Tier</th><th>Matched Keywords</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
