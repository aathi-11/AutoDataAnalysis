"""
Visualization Engine
Generates Plotly charts as JSON-serialisable dicts for the frontend.
"""
import json
import warnings
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio

warnings.filterwarnings("ignore")

PALETTE = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
    "#ef4444", "#ec4899", "#14b8a6", "#f97316", "#84cc16",
]
THEME_BG = "#0f0f1e"
CARD_BG = "#13131f"
TEXT = "#e2e8f0"


def _fig_to_dict(fig) -> dict:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=THEME_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return json.loads(pio.to_json(fig, pretty=False))


def _sample_rows(df: pd.DataFrame, max_rows: int = 400) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    return df.sample(max_rows, random_state=42).sort_index()


def _limit_cols(cols: List[str], max_cols: int) -> List[str]:
    return cols[:max_cols] if cols else []


def generate_charts(df: pd.DataFrame):
    charts = []
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    df_sample = _sample_rows(df, max_rows=500)

    # 1) Missing Values Heatmap
    if df.isnull().sum().sum() > 0:
        miss = df_sample.isnull().astype(int)
        fig = px.imshow(
            miss.T,
            aspect="auto",
            color_continuous_scale=[[0, CARD_BG], [1, "#ef4444"]],
            labels=dict(x="Row", y="Column", color="Missing"),
        )
        fig.update_layout(title="Missing Values Heatmap", height=380)
        fig.update_xaxes(showticklabels=False)
        charts.append({"title": "Missing Values Heatmap", "plotly": _fig_to_dict(fig)})

    # 2) Numeric Distributions
    for i, col in enumerate(_limit_cols(num_cols, 4)):
        fig = px.histogram(df_sample, x=col, nbins=30, title=f"Distribution: {col}")
        fig.update_traces(marker_color=PALETTE[i % len(PALETTE)], opacity=0.85)
        charts.append({"title": f"Distribution: {col}", "plotly": _fig_to_dict(fig)})

    # 3) Box Plot (Outliers View)
    if num_cols:
        box_cols = _limit_cols(num_cols, 10)
        melt = df_sample[box_cols].melt(var_name="column", value_name="value")
        fig = px.box(melt, x="column", y="value", points="outliers", title="Box Plots")
        fig.update_traces(marker_size=4)
        fig.update_xaxes(tickangle=25)
        charts.append({"title": "Box Plots (Outlier View)", "plotly": _fig_to_dict(fig)})

    # 4) Correlation Heatmap
    if len(num_cols) >= 2:
        corr_cols = _limit_cols(num_cols, 12)
        corr = df[corr_cols].corr()
        fig = px.imshow(
            corr,
            text_auto=True,
            color_continuous_scale="RdBu",
            zmin=-1,
            zmax=1,
            title="Correlation Heatmap",
        )
        charts.append({"title": "Correlation Heatmap", "plotly": _fig_to_dict(fig)})

    # 5) Categorical Bar Charts
    for i, col in enumerate(_limit_cols(cat_cols, 4)):
        vc = df_sample[col].value_counts().head(12)
        if len(vc) < 2:
            continue
        fig = px.bar(
            x=vc.values,
            y=[str(v) for v in vc.index],
            orientation="h",
            title=f"'{col}' Value Counts",
        )
        fig.update_traces(marker_color=PALETTE[i % len(PALETTE)])
        fig.update_layout(yaxis=dict(autorange="reversed"))
        charts.append({"title": f"'{col}' Value Counts", "plotly": _fig_to_dict(fig)})

    # 6) Scatter Matrix
    if 2 <= len(num_cols) <= 6:
        sm_cols = _limit_cols(num_cols, 5)
        sm_sample = df_sample[sm_cols].dropna()
        if len(sm_sample) >= 5:
            fig = px.scatter_matrix(
                sm_sample,
                dimensions=sm_cols,
                title="Scatter Matrix",
                color_discrete_sequence=[PALETTE[0]],
            )
            fig.update_traces(diagonal_visible=False, marker=dict(size=4, opacity=0.6))
            charts.append({"title": "Scatter Matrix", "plotly": _fig_to_dict(fig)})

    return charts
