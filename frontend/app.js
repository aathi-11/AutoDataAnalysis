/* ═══════════════════════════════════════════════════
   AutoAnalyst — Frontend Logic
   ═══════════════════════════════════════════════════ */

const API = "http://127.0.0.1:8000";
let analysisData = null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const dropZone       = document.getElementById("drop-zone");
const fileInput      = document.getElementById("file-input");
const uploadCard     = document.getElementById("upload-card");
const selectedFile   = document.getElementById("selected-file");
const fileNameEl     = document.getElementById("file-name-display");
const fileSizeEl     = document.getElementById("file-size-display");
const clearBtn       = document.getElementById("clear-btn");
const analyzeBtn     = document.getElementById("analyze-btn");
const progressSec    = document.getElementById("progress-section");
const progressBar    = document.getElementById("progress-bar");
const progressLabel  = document.getElementById("progress-label");
const reportSec      = document.getElementById("report-section");
const navReport      = document.getElementById("nav-report");
const errorToast     = document.getElementById("error-toast");
const errorMsg       = document.getElementById("error-message");
const downloadBtn    = document.getElementById("download-btn");

let selectedFileObj  = null;

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatBytes(b) {
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
  return (b / 1048576).toFixed(1) + " MB";
}
function fmtNum(v, dec = 2) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(dec);
  return v;
}
function showError(msg) {
  errorMsg.textContent = msg;
  errorToast.classList.remove("hidden");
  setTimeout(() => errorToast.classList.add("hidden"), 6000);
}
function md(text) {
  // simple bold/italic renderer
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g,     "<em>$1</em>");
}

// ── File selection ─────────────────────────────────────────────────────────────
function setFile(file) {
  if (!file) return;
  if (!file.name.endsWith(".csv")) { showError("Only CSV files are supported."); return; }
  selectedFileObj = file;
  fileNameEl.textContent = file.name;
  fileSizeEl.textContent = formatBytes(file.size);
  dropZone.classList.add("hidden");
  selectedFile.classList.remove("hidden");
}
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
clearBtn.addEventListener("click", () => {
  selectedFileObj = null;
  fileInput.value = "";
  selectedFile.classList.add("hidden");
  dropZone.classList.remove("hidden");
});

// Drag & drop
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  setFile(e.dataTransfer.files[0]);
});
dropZone.addEventListener("click", () => fileInput.click());

// ── Progress animation ─────────────────────────────────────────────────────────
const STEPS = [
  { id: "step-upload", label: "Uploading file…",        pct: 15 },
  { id: "step-clean",  label: "Cleaning data…",          pct: 35 },
  { id: "step-eda",    label: "Running EDA…",            pct: 60 },
  { id: "step-viz",    label: "Generating charts…",      pct: 85 },
  { id: "step-report", label: "Assembling report…",      pct: 100 },
];
let stepIdx = 0;
let stepTimer = null;

function startProgress() {
  stepIdx = 0;
  STEPS.forEach(s => {
    const el = document.getElementById(s.id);
    el.classList.remove("active", "done");
  });
  progressBar.style.width = "0%";
  advanceStep();
  stepTimer = setInterval(advanceStep, 1800);
}
function advanceStep() {
  if (stepIdx >= STEPS.length) { clearInterval(stepTimer); return; }
  const s = STEPS[stepIdx];
  if (stepIdx > 0) {
    document.getElementById(STEPS[stepIdx - 1].id).classList.remove("active");
    document.getElementById(STEPS[stepIdx - 1].id).classList.add("done");
  }
  document.getElementById(s.id).classList.add("active");
  progressLabel.textContent = s.label;
  progressBar.style.width = s.pct + "%";
  stepIdx++;
}
function finishProgress() {
  clearInterval(stepTimer);
  STEPS.forEach(s => {
    const el = document.getElementById(s.id);
    el.classList.remove("active");
    el.classList.add("done");
  });
  progressBar.style.width = "100%";
  progressLabel.textContent = "Analysis complete! ✨";
}

// ── Analysis ──────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  if (!selectedFileObj) { showError("Please select a CSV file first."); return; }

  // Show progress, hide upload
  uploadCard.closest("section").classList.add("hidden");
  reportSec.classList.add("hidden");
  progressSec.classList.remove("hidden");
  startProgress();

  const form = new FormData();
  form.append("file", selectedFileObj);

  try {
    const res = await fetch(`${API}/analyze`, { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Server error");
    }
    analysisData = await res.json();
    finishProgress();
    setTimeout(() => {
      progressSec.classList.add("hidden");
      renderReport(analysisData);
      reportSec.classList.remove("hidden");
      navReport.style.display = "";
      document.getElementById("report-section").scrollIntoView({ behavior: "smooth" });
    }, 800);
  } catch (err) {
    progressSec.classList.add("hidden");
    uploadCard.closest("section").classList.remove("hidden");
    showError("Analysis failed: " + err.message);
    console.error(err);
  }
});

// ── Tabs ──────────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.remove("hidden");
  });
});

// ── RENDER REPORT ─────────────────────────────────────────────────────────────
function renderReport(data) {
  // Title
  document.getElementById("report-filename").textContent = data.filename;
  document.getElementById("report-ts").textContent = "Generated on " + new Date().toLocaleString();

  // KPI cards
  renderKPIs(data);

  // Tabs
  renderCleaning(data.cleaning);
  renderEDA(data.eda);
  renderCharts(data.charts);
  renderPreview(data.preview, data.preview_cols);
  renderInsights(data.eda.insights);
}

// ── KPI ───────────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const ov  = data.eda.overview;
  const cl  = data.cleaning;
  const score = cl.quality_score;

  const scoreColor = score >= 80 ? "kpi-success" : score >= 60 ? "kpi-warning" : "kpi-danger";

  const kpis = [
    { label: "Quality Score",    value: score + "%",        sub: "Post-cleaning",      cls: scoreColor  },
    { label: "Rows",             value: ov.rows.toLocaleString(), sub: `${cl.rows_removed} removed`, cls: "kpi-accent" },
    { label: "Columns",          value: ov.columns,         sub: `${ov.numeric_columns} numeric`, cls: "kpi-info" },
    { label: "Missing Cells",    value: ov.missing_cells.toLocaleString(), sub: ov.missing_pct + "%",  cls: ov.missing_pct > 5 ? "kpi-warning" : "kpi-success" },
    { label: "Numeric Cols",     value: ov.numeric_columns, sub: "features",           cls: "kpi-accent" },
    { label: "Categorical Cols", value: ov.categorical_columns, sub: "categories",     cls: "kpi-info"   },
    { label: "Memory",           value: ov.memory_usage_kb.toFixed(1) + " KB", sub: "clean dataset", cls: "kpi-accent" },
    { label: "Cleaning Steps",   value: cl.steps.length,    sub: "applied",            cls: "kpi-success" },
  ];

  document.getElementById("kpi-row").innerHTML = kpis.map(k => `
    <div class="kpi-card">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value ${k.cls}">${k.value}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>
  `).join("");
}

// ── CLEANING ──────────────────────────────────────────────────────────────────
function renderCleaning(cl) {
  const panel = document.getElementById("tab-cleaning");

  const summaryHtml = `
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:24px;">
      <div class="kpi-card"><div class="kpi-label">Original Shape</div><div class="kpi-value kpi-accent" style="font-size:1.3rem;">${cl.original_rows} × ${cl.original_cols}</div></div>
      <div class="kpi-card"><div class="kpi-label">Cleaned Shape</div><div class="kpi-value kpi-success" style="font-size:1.3rem;">${cl.cleaned_rows} × ${cl.cleaned_cols}</div></div>
      <div class="kpi-card"><div class="kpi-label">Rows Removed</div><div class="kpi-value kpi-warning" style="font-size:1.3rem;">${cl.rows_removed}</div></div>
      <div class="kpi-card"><div class="kpi-label">Quality Score</div><div class="kpi-value ${cl.quality_score>=80?'kpi-success':cl.quality_score>=60?'kpi-warning':'kpi-danger'}" style="font-size:1.3rem;">${cl.quality_score}%</div></div>
    </div>
  `;

  const stepsHtml = cl.steps.length === 0
    ? `<div class="no-insights">✅ No cleaning required — data looks pristine!</div>`
    : `<div class="clean-grid">${cl.steps.map(s => {
        let detail = "";
        if (typeof s.detail === "string") {
          detail = `<p>${s.detail}</p>`;
        } else if (typeof s.detail === "object") {
          detail = `<ul>${Object.entries(s.detail).map(([k, v]) => `<li><strong>${k}</strong>: ${v}</li>`).join("")}</ul>`;
        }
        return `<div class="clean-step"><h4>🔧 ${s.step}</h4>${detail}</div>`;
      }).join("")}</div>`;

  panel.innerHTML = summaryHtml + `<h3 style="margin-bottom:16px;color:var(--accent);">🔧 Cleaning Steps Applied</h3>` + stepsHtml;
}

// ── EDA ───────────────────────────────────────────────────────────────────────
function renderEDA(eda) {
  const panel = document.getElementById("tab-eda");
  let html = "";

  // Column cards
  html += `<div class="eda-section"><h3>🗂 Column Analysis</h3><div class="col-cards">`;
  for (const col of eda.columns) {
    const missingPct = col.missing_pct || 0;
    const barColor   = missingPct > 30 ? "var(--danger)" : missingPct > 10 ? "var(--warning)" : "var(--success)";
    let statsHtml = "";

    if (col.mean !== undefined) {
      statsHtml = `
        <div class="stat-row"><span>Mean</span><span>${fmtNum(col.mean)}</span></div>
        <div class="stat-row"><span>Std Dev</span><span>${fmtNum(col.std)}</span></div>
        <div class="stat-row"><span>Min</span><span>${fmtNum(col.min)}</span></div>
        <div class="stat-row"><span>Median</span><span>${fmtNum(col.median)}</span></div>
        <div class="stat-row"><span>Max</span><span>${fmtNum(col.max)}</span></div>
        <div class="stat-row"><span>Skewness</span><span>${fmtNum(col.skewness)}</span></div>
        <div class="stat-row"><span>Kurtosis</span><span>${fmtNum(col.kurtosis)}</span></div>
      `;
    } else if (col.top_values) {
      statsHtml = Object.entries(col.top_values).slice(0, 4).map(([k, v]) =>
        `<div class="stat-row"><span>${k}</span><span>${v}</span></div>`
      ).join("");
    }

    html += `
      <div class="col-card">
        <div class="col-card-header">
          <span class="col-name">${col.name}</span>
          <span class="col-dtype">${col.dtype}</span>
        </div>
        <div class="col-stats">
          <div class="stat-row"><span>Unique</span><span>${col.unique} (${col.unique_pct}%)</span></div>
          <div class="stat-row"><span>Missing</span><span style="color:${barColor}">${col.missing} (${missingPct}%)</span></div>
          ${statsHtml}
        </div>
        <div class="missing-bar-wrap">
          <div class="missing-bar" style="width:${missingPct}%;background:${barColor}"></div>
        </div>
      </div>
    `;
  }
  html += "</div></div>";

  // Top correlations table
  if (eda.top_correlations && eda.top_correlations.length > 0) {
    html += `
      <div class="eda-section">
        <h3>🔗 Top Correlations</h3>
        <div class="corr-table-wrap">
          <table class="data-table">
            <thead><tr><th>#</th><th>Column A</th><th>Column B</th><th>Correlation</th><th>Strength</th></tr></thead>
            <tbody>
              ${eda.top_correlations.map((p, i) => {
                const abs = Math.abs(p.corr);
                const strength = abs > 0.8 ? "🔴 Strong" : abs > 0.5 ? "🟡 Moderate" : "🟢 Weak";
                const color    = abs > 0.8 ? "var(--danger)" : abs > 0.5 ? "var(--warning)" : "var(--success)";
                return `<tr>
                  <td>${i + 1}</td>
                  <td>${p.col1}</td>
                  <td>${p.col2}</td>
                  <td style="color:${color};font-weight:600">${p.corr}</td>
                  <td>${strength}</td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // Categorical summary
  if (eda.categorical_summary) {
    html += `<div class="eda-section"><h3>🏷 Categorical Columns</h3><div class="col-cards">`;
    for (const [col, info] of Object.entries(eda.categorical_summary)) {
      html += `
        <div class="col-card">
          <div class="col-card-header">
            <span class="col-name">${col}</span>
            <span class="col-dtype">categorical</span>
          </div>
          <div class="col-stats">
            <div class="stat-row"><span>Unique Values</span><span>${info.unique_count}</span></div>
            ${Object.entries(info.top_values).slice(0, 5).map(([k, v]) =>
              `<div class="stat-row"><span>${k}</span><span>${v}</span></div>`
            ).join("")}
          </div>
        </div>
      `;
    }
    html += "</div></div>";
  }

  panel.innerHTML = html;
}

// ── CHARTS ─────────────────────────────────────────────────────────────────────
function renderCharts(charts) {
  const panel = document.getElementById("tab-charts");
  if (!charts || charts.length === 0) {
    panel.innerHTML = `<div class="no-insights">No charts generated (not enough numeric columns).</div>`;
    return;
  }
  const icons = ["📊","📈","📉","🔥","📋","🔵","🟣"];
  panel.innerHTML = `<div class="charts-grid">${charts.map((c, i) => `
    <div class="chart-card">
      <div class="chart-title">${icons[i % icons.length]} ${c.title}</div>
      <img src="data:image/png;base64,${c.img}" alt="${c.title}" loading="lazy" />
    </div>
  `).join("")}</div>`;
}

// ── PREVIEW ────────────────────────────────────────────────────────────────────
function renderPreview(rows, cols) {
  const panel = document.getElementById("tab-preview");
  if (!rows || rows.length === 0) {
    panel.innerHTML = `<div class="no-insights">No preview data available.</div>`;
    return;
  }
  panel.innerHTML = `
    <p style="color:var(--text3);font-size:0.82rem;margin-bottom:12px;">Showing first ${rows.length} rows · ${cols.length} columns</p>
    <div class="preview-wrap">
      <table class="preview-table">
        <thead>
          <tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map(row => `<tr>${cols.map(c => {
            const v = row[c];
            return `<td title="${v ?? ""}">${v === null || v === undefined ? '<span style="color:var(--text3)">null</span>' : v}</td>`;
          }).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// ── INSIGHTS ───────────────────────────────────────────────────────────────────
function renderInsights(insights) {
  const panel = document.getElementById("tab-insights");
  if (!insights || insights.length === 0) {
    panel.innerHTML = `<div class="no-insights">🎉 No critical issues found — dataset looks healthy!</div>`;
    return;
  }
  const icons = ["💡","⚠️","📌","🔍","📐","🧮"];
  panel.innerHTML = `<div class="insight-list">${insights.map((ins, i) => `
    <div class="insight-card">
      <div class="insight-icon">${icons[i % icons.length]}</div>
      <div class="insight-text">${md(ins)}</div>
    </div>
  `).join("")}</div>`;
}

// ── DOWNLOAD REPORT ────────────────────────────────────────────────────────────
downloadBtn.addEventListener("click", () => {
  if (!analysisData) return;
  const d = analysisData;
  const ov = d.eda.overview;
  const cl = d.cleaning;

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>AutoAnalyst Report — ${d.filename}</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#0f0f1e;color:#e2e8f0;margin:0;padding:40px;}
  h1{color:#6366f1;font-size:2rem;} h2{color:#8b5cf6;margin-top:32px;border-bottom:1px solid #2a2a45;padding-bottom:8px;}
  .kpi{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin:20px 0;}
  .kpi-c{background:#1a1a2e;border:1px solid #2a2a45;border-radius:10px;padding:16px;}
  .kpi-c .l{font-size:0.75rem;color:#64748b;text-transform:uppercase;margin-bottom:6px;}
  .kpi-c .v{font-size:1.6rem;font-weight:800;color:#6366f1;}
  table{width:100%;border-collapse:collapse;font-size:0.85rem;font-family:monospace;}
  th{background:#1a1a2e;color:#6366f1;padding:10px;text-align:left;border-bottom:1px solid #2a2a45;}
  td{padding:8px 10px;border-bottom:1px solid #1a1a2e;color:#94a3b8;}
  img{max-width:100%;border-radius:10px;margin:12px 0;}
  .step{background:#1a1a2e;border-left:3px solid #6366f1;padding:12px 16px;border-radius:6px;margin-bottom:10px;}
  .ins{background:#1a1a2e;border-left:3px solid #f59e0b;padding:12px 16px;border-radius:6px;margin-bottom:10px;}
  footer{margin-top:60px;padding-top:16px;border-top:1px solid #2a2a45;color:#64748b;font-size:0.8rem;text-align:center;}
</style>
</head>
<body>
<h1>📊 AutoAnalyst Report</h1>
<p style="color:#64748b">File: <strong style="color:#e2e8f0">${d.filename}</strong> &nbsp;·&nbsp; Generated: ${new Date().toLocaleString()}</p>

<h2>📋 Dataset Overview</h2>
<div class="kpi">
  <div class="kpi-c"><div class="l">Quality Score</div><div class="v">${cl.quality_score}%</div></div>
  <div class="kpi-c"><div class="l">Rows (clean)</div><div class="v">${ov.rows}</div></div>
  <div class="kpi-c"><div class="l">Columns</div><div class="v">${ov.columns}</div></div>
  <div class="kpi-c"><div class="l">Missing %</div><div class="v">${ov.missing_pct}%</div></div>
  <div class="kpi-c"><div class="l">Numeric Cols</div><div class="v">${ov.numeric_columns}</div></div>
  <div class="kpi-c"><div class="l">Cat Cols</div><div class="v">${ov.categorical_columns}</div></div>
</div>

<h2>🧹 Cleaning Steps</h2>
${cl.steps.map(s => {
  let det = typeof s.detail === "string" ? s.detail
    : Object.entries(s.detail).map(([k,v])=>`• ${k}: ${v}`).join("<br/>");
  return `<div class="step"><strong>${s.step}</strong><br/><small style="color:#94a3b8">${det}</small></div>`;
}).join("") || "<p style='color:#64748b'>No cleaning required.</p>"}

<h2>📈 Column Statistics</h2>
<table>
  <thead><tr><th>Column</th><th>Type</th><th>Unique</th><th>Missing %</th><th>Mean</th><th>Std</th><th>Min</th><th>Max</th></tr></thead>
  <tbody>
    ${d.eda.columns.map(c => `<tr>
      <td>${c.name}</td><td>${c.dtype}</td><td>${c.unique}</td><td>${c.missing_pct}%</td>
      <td>${c.mean !== undefined ? fmtNum(c.mean) : "—"}</td>
      <td>${c.std !== undefined ? fmtNum(c.std) : "—"}</td>
      <td>${c.min !== undefined ? fmtNum(c.min) : "—"}</td>
      <td>${c.max !== undefined ? fmtNum(c.max) : "—"}</td>
    </tr>`).join("")}
  </tbody>
</table>

${d.eda.top_correlations ? `
<h2>🔗 Top Correlations</h2>
<table>
  <thead><tr><th>Column A</th><th>Column B</th><th>Correlation</th></tr></thead>
  <tbody>${d.eda.top_correlations.map(p=>`<tr><td>${p.col1}</td><td>${p.col2}</td><td>${p.corr}</td></tr>`).join("")}</tbody>
</table>` : ""}

<h2>💡 Insights & Recommendations</h2>
${d.eda.insights.length > 0
  ? d.eda.insights.map(i=>`<div class="ins">${i.replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")}</div>`).join("")
  : "<p style='color:#64748b'>✅ No critical issues detected.</p>"}

<h2>🎨 Visualisations</h2>
${d.charts.map(c=>`<div><h3 style="color:#94a3b8;font-size:0.9rem;margin-bottom:6px">${c.title}</h3><img src="data:image/png;base64,${c.img}" alt="${c.title}"/></div>`).join("")}

<footer>AutoAnalyst · Autonomous Data Analysis Platform</footer>
</body></html>`;

  const blob = new Blob([html], { type: "text/html" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `AutoAnalyst_Report_${d.filename.replace(".csv","")}_${Date.now()}.html`;
  a.click();
  URL.revokeObjectURL(url);
});
