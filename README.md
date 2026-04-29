# ⚡ AutoAnalyst — Autonomous Data Analysis Platform

Upload any CSV file and instantly get **data cleaning**, **exploratory data analysis (EDA)**, **visualizations**, and a **downloadable report** — all automated, no code needed.

---

## 🚀 What It Can Do

### 🧹 Data Cleaning (Automatic)
- Standardises column names (lowercase, underscores)
- Infers and corrects data types (object → numeric / datetime)
- Removes duplicate rows
- Imputes missing values — **median** for numbers, **mode** for categories
- Drops columns with more than 60% missing data
- Caps outliers using the **IQR × 1.5** method

### 📊 Exploratory Data Analysis (EDA)
- Dataset shape, memory usage, missing cell counts
- Per-column statistics: mean, std, min, max, median, Q1, Q3
- Skewness & kurtosis for numeric columns
- Top value frequencies for categorical columns
- Full **correlation matrix** with top correlated pairs ranked

### 🎨 Auto-Generated Visualizations (Dark-Themed)
| Chart | Description |
|-------|-------------|
| Missing Values Heatmap | Shows where nulls are across all columns |
| Numeric Distributions | Histogram + KDE curve for every numeric column |
| Box Plots | Normalised box plots for outlier inspection |
| Correlation Heatmap | Lower-triangle heatmap with annotations |
| Categorical Bar Charts | Horizontal bar charts for top categories |
| Scatter Matrix | Pairplot for up to 6 numeric columns |

### 💡 Insights & Recommendations
- Flags skewed columns and suggests log-transform
- Warns about high missing data percentages
- Detects strong multicollinearity between features

### 📋 Report
- Interactive web report with **5 tabs**: Cleaning · EDA · Visualisations · Data Preview · Insights
- **KPI cards**: quality score, row/column counts, memory, cleaning steps applied
- **Download** a full self-contained HTML report to your machine

---

## 🗂 Project Structure

```
Auto Data Analyst/
├── backend/
│   ├── main.py              # FastAPI app — /analyze endpoint
│   ├── cleaner.py           # Data cleaning engine
│   ├── eda.py               # EDA statistics engine
│   ├── visualizer.py        # Chart generation (Matplotlib + Seaborn)
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Main UI page
│   ├── style.css            # Dark premium theme
│   └── app.js               # Upload, API calls, report rendering
└── README.md
```

---

## 🛠 Requirements

- **Python 3.9+** — [Download here](https://python.org)
- **pip** (comes with Python)
- A modern web browser (Chrome, Edge, Firefox)

---

## ▶️ How to Run (Terminal Instructions)

### Step 1 — Install Python dependencies

Open a terminal, navigate to the backend folder, and install packages:

```bash
cd "f:\AIML\Auto Data Analyst\backend"
pip install -r requirements.txt
```

> ⏳ This only needs to be done **once**.

---

### Step 2 — Start the Backend API

In the same terminal (or a new one in the `backend` folder):

```bash
cd "f:\AIML\Auto Data Analyst\backend"
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

> ✅ Keep this terminal open while using the app.

---

### Step 3 — Start the Frontend Server

Open a **second terminal** and run:

```bash
cd "f:\AIML\Auto Data Analyst\frontend"
python -m http.server 3000
```

You should see:
```
Serving HTTP on 0.0.0.0 port 3000 ...
```

> ✅ Keep this terminal open too.

---

### Step 4 — Open the App

Open your browser and go to:

```
http://localhost:3000
```

---

## 🔗 Available URLs

| URL | Purpose |
|-----|---------|
| `http://localhost:3000` | Main application (frontend) |
| `http://127.0.0.1:8000` | Backend API |
| `http://127.0.0.1:8000/docs` | Interactive API documentation (Swagger UI) |
| `http://127.0.0.1:8000/health` | API health check |

---

## ⏹ How to Stop

- In each terminal, press **`CTRL + C`** to stop the server.

---

## 🧪 Quick Test

You can test the backend directly using curl:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" -F "file=@your_data.csv"
```

Or visit `http://127.0.0.1:8000/docs` and use the built-in Swagger UI to upload a file interactively.

---

## 📦 Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.111.0 | Web API framework |
| uvicorn | 0.30.0 | ASGI server |
| python-multipart | 0.0.9 | File upload handling |
| pandas | 2.2.2 | Data processing |
| numpy | 1.26.4 | Numerical operations |
| matplotlib | 3.9.0 | Chart generation |
| seaborn | 0.13.2 | Statistical visualizations |
| scipy | 1.13.1 | KDE and statistical functions |

---

## ⚠️ Troubleshooting

**Port already in use?**
```bash
# Use a different port
python -m uvicorn main:app --port 8001
# or for frontend
python -m http.server 3001
```
Then update the `API` variable in `frontend/app.js` to match.

**pip not found?**
```bash
python -m pip install -r requirements.txt
```

**Charts not showing?**
Make sure `matplotlib` and `seaborn` installed correctly:
```bash
pip install matplotlib seaborn --upgrade
```
