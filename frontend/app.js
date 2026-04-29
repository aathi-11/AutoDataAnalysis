/* ═══════════════════════════════════════════════════
   AutoAnalyst — Frontend Logic (Phase 1)
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
  { id: "step-upload",  label: "Uploading file…",        pct: 10 },
  { id: "step-clean",   label: "Cleaning data…",         pct: 25 },
  { id: "step-eda",     label: "Running EDA…",           pct: 40 },
  { id: "step-viz",     label: "Generating charts…",     pct: 50 },
  { id: "step-ml",      label: "Training AutoML…",       pct: 65 },
  { id: "step-anomaly", label: "Detecting Anomalies…",   pct: 80 },
  { id: "step-ts",      label: "Time Series Analysis…",  pct: 90 },
  { id: "step-report",  label: "Assembling report…",     pct: 100 },
];
let stepIdx = 0;
let stepTimer = null;

function startProgress() {
  stepIdx = 0;
  STEPS.forEach(s => {
    const el = document.getElementById(s.id);
    if(el) el.classList.remove("active", "done");
  });
  progressBar.style.width = "0%";
  advanceStep();
  stepTimer = setInterval(advanceStep, 2000);
}
function advanceStep() {
  if (stepIdx >= STEPS.length) { clearInterval(stepTimer); return; }
  const s = STEPS[stepIdx];
  if (stepIdx > 0) {
    const prev = document.getElementById(STEPS[stepIdx - 1].id);
    if(prev) { prev.classList.remove("active"); prev.classList.add("done"); }
  }
  const curr = document.getElementById(s.id);
  if(curr) curr.classList.add("active");
  progressLabel.textContent = s.label;
  progressBar.style.width = s.pct + "%";
  stepIdx++;
}
function finishProgress() {
  clearInterval(stepTimer);
  STEPS.forEach(s => {
    const el = document.getElementById(s.id);
    if(el) { el.classList.remove("active"); el.classList.add("done"); }
  });
  progressBar.style.width = "100%";
  progressLabel.textContent = "Analysis complete! ✨";
}

// ── Analysis ──────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  if (!selectedFileObj) { showError("Please select a CSV file first."); return; }

  uploadCard.closest("section").classList.add("hidden");
  reportSec.classList.add("hidden");
  progressSec.classList.remove("hidden");
  startProgress();

  const form = new FormData();
  form.append("file", selectedFileObj);

  try {
    const res = await fetch(`${API}/analyze/phase1`, { method: "POST", body: form });
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
  document.getElementById("report-filename").textContent = data.filename;
  document.getElementById("report-ts").textContent = "Generated on " + new Date().toLocaleString();

  renderKPIs(data);

  renderCleaning(data.cleaning);
  renderEDA(data.eda);
  renderCharts(data.charts);
  renderQuality(data.quality);
  renderML(data.ml);
  renderAnomaly(data.anomaly);
  renderTimeSeries(data.time_series);
  renderPreview(data.preview, data.preview_cols);
  renderInsights(data.eda.insights);
}

// ── KPI ───────────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const ov  = data.eda.overview;
  const score = data.quality ? data.quality.overall_score : data.cleaning.quality_score;
  const scoreColor = score >= 80 ? "kpi-success" : score >= 60 ? "kpi-warning" : "kpi-danger";

  const kpis = [
    { label: "Quality Score",    value: score + "%",        sub: "Phase 1 Assessment",      cls: scoreColor  },
    { label: "Rows",             value: ov.rows.toLocaleString(), sub: `${data.cleaning.rows_removed} removed`, cls: "kpi-accent" },
    { label: "Columns",          value: ov.columns,         sub: `${ov.numeric_columns} numeric`, cls: "kpi-info" },
    { label: "Missing Cells",    value: ov.missing_cells.toLocaleString(), sub: ov.missing_pct + "%",  cls: ov.missing_pct > 5 ? "kpi-warning" : "kpi-success" },
  ];

  document.getElementById("kpi-row").innerHTML = kpis.map(k => `
    <div class="kpi-card">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value ${k.cls}">${k.value}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>
  `).join("");
}

// ── PHASE 1 RENDERERS ─────────────────────────────────────────────────────────

function renderQuality(quality) {
  const panel = document.getElementById("tab-quality");
  if(!quality) { panel.innerHTML = `<div class="no-insights">Quality data not available.</div>`; return; }
  
  let html = `<h3>🏅 Data Quality Scorecard</h3>`;
  html += `<div style="display:flex;gap:20px;margin-bottom:20px;">
    <div class="kpi-card" style="flex:1"><div class="kpi-label">Overall Score</div><div class="kpi-value ${quality.overall_score>=80?'kpi-success':quality.overall_score>=60?'kpi-warning':'kpi-danger'}">${quality.overall_score}%</div><div class="kpi-sub">Grade: ${quality.overall_grade}</div></div>
  </div>`;
  
  html += `<h4>Dimensions</h4><div class="col-cards">`;
  quality.dimensions.forEach(d => {
    html += `<div class="col-card">
      <div class="col-card-header"><span class="col-name">${d.name}</span><span class="col-dtype">Weight: ${d.weight}%</span></div>
      <div class="col-stats">
        <div class="stat-row"><span>Score</span><span class="${d.score>=80?'kpi-success':d.score>=60?'kpi-warning':'kpi-danger'}">${d.score}% (Grade ${d.grade})</span></div>
        <div class="stat-row"><span style="white-space:normal;color:var(--text2)">${d.description}</span></div>
      </div>
    </div>`;
  });
  html += `</div>`;
  
  if(quality.issues && quality.issues.length > 0) {
    html += `<h4 style="margin-top:20px;color:var(--warning);">Issues Detected</h4><ul>`;
    quality.issues.forEach(iss => { html += `<li style="margin-bottom:8px;">${iss}</li>`; });
    html += `</ul>`;
  }
  
  panel.innerHTML = html;
}

function renderML(ml) {
  const panel = document.getElementById("tab-ml");
  if(!ml || ml.error) { panel.innerHTML = `<div class="no-insights">${ml?.error || "AutoML not available."}</div>`; return; }
  
  let html = `<h3>🤖 AutoML Predictions</h3>`;
  html += `<div class="kpi-card" style="margin-bottom:20px;">
    <div class="kpi-label">Target Column</div><div class="kpi-value kpi-accent">${ml.target_column}</div>
    <div class="kpi-sub">Task Type: ${ml.task_type}</div>
  </div>`;
  
  html += `<h4>Model Leaderboard</h4>`;
  html += `<table class="preview-table"><thead><tr><th>Model</th>`;
  
  if(ml.task_type === 'classification') {
    html += `<th>Accuracy</th><th>F1 Score</th><th>Precision</th><th>Recall</th></tr></thead><tbody>`;
  } else {
    html += `<th>R² Score</th><th>MAE</th><th>RMSE</th></tr></thead><tbody>`;
  }
  
  ml.models.forEach(m => {
    if(m.error) {
      html += `<tr><td>${m.model}</td><td colspan="4" style="color:var(--danger)">Error: ${m.error}</td></tr>`;
    } else {
      let isBest = m.model === ml.best_model;
      let nameStr = isBest ? `<strong>${m.model} 🏆</strong>` : m.model;
      if(ml.task_type === 'classification') {
        html += `<tr><td>${nameStr}</td><td>${m.metrics.accuracy}</td><td>${m.metrics.f1_score}</td><td>${m.metrics.precision}</td><td>${m.metrics.recall}</td></tr>`;
      } else {
        html += `<tr><td>${nameStr}</td><td>${m.metrics.r2}</td><td>${m.metrics.mae}</td><td>${m.metrics.rmse}</td></tr>`;
      }
    }
  });
  html += `</tbody></table>`;
  
  if(ml.feature_importances) {
    html += `<h4 style="margin-top:20px;">Top Feature Importances (${ml.best_model})</h4>`;
    html += `<div class="col-cards">`;
    ml.feature_importances.slice(0, 5).forEach(f => {
      html += `<div class="col-card" style="padding:10px;">
        <div class="stat-row" style="margin:0;"><span>${f.feature}</span><span class="kpi-info">${f.importance.toFixed(4)}</span></div>
      </div>`;
    });
    html += `</div>`;
  }
  
  panel.innerHTML = html;
}

function renderAnomaly(anomaly) {
  const panel = document.getElementById("tab-anomaly");
  if(!anomaly || anomaly.error) { panel.innerHTML = `<div class="no-insights">${anomaly?.error || "Anomaly detection not available."}</div>`; return; }
  
  let html = `<h3>🚨 Anomaly Detection (Isolation Forest)</h3>`;
  html += `<div style="display:flex;gap:20px;margin-bottom:20px;">
    <div class="kpi-card" style="flex:1"><div class="kpi-label">Anomalies Detected</div><div class="kpi-value kpi-danger">${anomaly.total_anomalies}</div><div class="kpi-sub">${anomaly.anomaly_pct}% of dataset</div></div>
    <div class="kpi-card" style="flex:1"><div class="kpi-label">Algorithm</div><div class="kpi-value kpi-info">Isolation Forest</div><div class="kpi-sub">Contamination: ${anomaly.contamination_used}</div></div>
  </div>`;
  
  if(anomaly.total_anomalies > 0) {
    html += `<h4>Top Anomaly Drivers (Features)</h4><div class="col-cards">`;
    anomaly.top_anomaly_cols.forEach(c => {
      html += `<div class="col-card" style="padding:10px;">
        <div class="stat-row" style="margin:0;"><span>${c.col}</span><span class="kpi-warning">+${c.diff_pct}% diff</span></div>
      </div>`;
    });
    html += `</div>`;
    
    html += `<h4 style="margin-top:20px;">Sample Anomalous Rows</h4>`;
    let cols = ["row_index", "anomaly_score", ...anomaly.numeric_cols_used.slice(0, 5)];
    html += `<div class="preview-wrap"><table class="preview-table"><thead><tr>${cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>`;
    anomaly.anomaly_rows.slice(0, 10).forEach(r => {
      html += `<tr>${cols.map(c => `<td>${r[c]}</td>`).join('')}</tr>`;
    });
    html += `</tbody></table></div>`;
  } else {
    html += `<div class="no-insights">No significant anomalies detected in numeric columns.</div>`;
  }
  
  panel.innerHTML = html;
}

function renderTimeSeries(ts) {
  const panel = document.getElementById("tab-timeseries");
  if(!ts || ts.error) { panel.innerHTML = `<div class="no-insights">${ts?.error || "Time series analysis not available."}</div>`; return; }
  
  let html = `<h3>📈 Time Series Analysis</h3>`;
  html += `<div class="kpi-card" style="margin-bottom:20px;">
    <div class="kpi-label">Datetime Column</div><div class="kpi-value kpi-accent">${ts.datetime_column}</div>
    <div class="kpi-sub">Range: ${ts.date_range.start.substring(0,10)} to ${ts.date_range.end.substring(0,10)} (Freq: ${ts.inferred_frequency})</div>
  </div>`;
  
  if(ts.columns) {
    html += `<h4>Numeric Series Characteristics</h4><div class="col-cards">`;
    for(const [col, data] of Object.entries(ts.columns)) {
      let st = data.stats;
      html += `<div class="col-card">
        <div class="col-card-header"><span class="col-name">${col}</span><span class="col-dtype">Trend: ${st.trend}</span></div>
        <div class="col-stats">
          <div class="stat-row"><span>Change</span><span class="${st.change_pct>0?'kpi-success':'kpi-danger'}">${st.change_pct?st.change_pct+'%':'—'}</span></div>
          <div class="stat-row"><span>Stationary (ADF)</span><span class="${data.stationarity.is_stationary?'kpi-success':'kpi-warning'}">${data.stationarity.is_stationary?'Yes':'No'}</span></div>
          <div class="stat-row"><span>Min / Max</span><span>${fmtNum(st.min)} / ${fmtNum(st.max)}</span></div>
        </div>
      </div>`;
    }
    html += `</div>`;
  }
  
  panel.innerHTML = html;
}

// ── OLD TABS (CLEANING, EDA, CHARTS, PREVIEW, INSIGHTS) ───────────────────────

function renderCleaning(cl) {
  const panel = document.getElementById("tab-cleaning");
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
  panel.innerHTML = `<h3 style="margin-bottom:16px;color:var(--accent);">🔧 Cleaning Steps Applied</h3>` + stepsHtml;
}

function renderEDA(eda) {
  const panel = document.getElementById("tab-eda");
  let html = `<div class="eda-section"><h3>🗂 Column Analysis</h3><div class="col-cards">`;
  for (const col of eda.columns) {
    const missingPct = col.missing_pct || 0;
    const barColor   = missingPct > 30 ? "var(--danger)" : missingPct > 10 ? "var(--warning)" : "var(--success)";
    let statsHtml = "";
    if (col.mean !== undefined) {
      statsHtml = `<div class="stat-row"><span>Mean</span><span>${fmtNum(col.mean)}</span></div>
        <div class="stat-row"><span>Std Dev</span><span>${fmtNum(col.std)}</span></div>
        <div class="stat-row"><span>Min</span><span>${fmtNum(col.min)}</span></div>
        <div class="stat-row"><span>Max</span><span>${fmtNum(col.max)}</span></div>`;
    } else if (col.top_values) {
      statsHtml = Object.entries(col.top_values).slice(0, 4).map(([k, v]) =>
        `<div class="stat-row"><span>${k}</span><span>${v}</span></div>`
      ).join("");
    }
    html += `<div class="col-card"><div class="col-card-header"><span class="col-name">${col.name}</span><span class="col-dtype">${col.dtype}</span></div>
      <div class="col-stats"><div class="stat-row"><span>Unique</span><span>${col.unique}</span></div>
      <div class="stat-row"><span>Missing</span><span style="color:${barColor}">${col.missing} (${missingPct}%)</span></div>${statsHtml}</div></div>`;
  }
  html += "</div></div>";
  panel.innerHTML = html;
}

function renderCharts(charts) {
  const panel = document.getElementById("tab-charts");
  if (!charts || charts.length === 0) {
    panel.innerHTML = `<div class="no-insights">No charts generated.</div>`; return;
  }
  
  panel.innerHTML = `<div class="charts-grid" id="charts-container"></div>`;
  const container = document.getElementById("charts-container");
  
  charts.forEach((c, i) => {
    const cardId = `chart-plot-${i}`;
    const cardHtml = `
      <div class="chart-card">
        <div class="chart-title">📊 ${c.title}</div>
        <div id="${cardId}" class="chart-plot" style="width:100%;min-height:360px;"></div>
      </div>
    `;
    container.insertAdjacentHTML("beforeend", cardHtml);
    
    // Render Plotly
    if (c.plotly) {
      Plotly.newPlot(cardId, c.plotly.data, c.plotly.layout, {responsive: true, displayModeBar: false});
    } else if (c.img) {
      document.getElementById(cardId).innerHTML = `<img src="data:image/png;base64,${c.img}" alt="${c.title}" loading="lazy" style="width:100%;border-radius:6px;margin-top:10px;"/>`;
    }
  });
}

function renderPreview(rows, cols) {
  const panel = document.getElementById("tab-preview");
  if (!rows || rows.length === 0) { panel.innerHTML = `<div class="no-insights">No preview data.</div>`; return; }
  panel.innerHTML = `<div class="preview-wrap"><table class="preview-table">
    <thead><tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr></thead>
    <tbody>${rows.map(row => `<tr>${cols.map(c => `<td>${row[c] ?? ""}</td>`).join("")}</tr>`).join("")}</tbody>
  </table></div>`;
}

function renderInsights(insights) {
  const panel = document.getElementById("tab-insights");
  if (!insights || insights.length === 0) {
    panel.innerHTML = `<div class="no-insights">🎉 No critical issues found.</div>`; return;
  }
  panel.innerHTML = `<div class="insight-list">${insights.map(ins => `
    <div class="insight-card"><div class="insight-icon">💡</div><div class="insight-text">${md(ins)}</div></div>
  `).join("")}</div>`;
}

// ── DOWNLOAD REPORT ────────────────────────────────────────────────────────────
downloadBtn.addEventListener("click", () => {
  if (!analysisData) return;
  alert("Report download functionality can be expanded for Phase 1 components. Basic download disabled temporarily to save tokens.");
});
