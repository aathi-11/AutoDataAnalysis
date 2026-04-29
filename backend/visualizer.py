"""
Visualization Engine
Generates base64-encoded chart images using Matplotlib & Seaborn.
"""
import io, base64, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

warnings.filterwarnings("ignore")

# ── Palette & style ────────────────────────────────────────────────────────────
PALETTE   = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
             "#ef4444", "#ec4899", "#14b8a6", "#f97316", "#84cc16"]
BG_COLOR  = "#0f0f1a"
CARD_COLOR = "#1a1a2e"
TEXT_COLOR = "#e2e8f0"
GRID_COLOR = "#2d2d4e"

def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=120)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return encoded


def _base_style(fig, ax_list=None):
    fig.patch.set_facecolor(BG_COLOR)
    if ax_list:
        for ax in (ax_list if isinstance(ax_list, list) else [ax_list]):
            ax.set_facecolor(CARD_COLOR)
            ax.tick_params(colors=TEXT_COLOR, labelsize=9)
            ax.xaxis.label.set_color(TEXT_COLOR)
            ax.yaxis.label.set_color(TEXT_COLOR)
            ax.title.set_color(TEXT_COLOR)
            for spine in ax.spines.values():
                spine.set_edgecolor(GRID_COLOR)
            ax.grid(color=GRID_COLOR, linestyle="--", linewidth=0.5, alpha=0.7)


def generate_charts(df: pd.DataFrame):
    charts = []
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # ── 1. Missing Values Heatmap ──────────────────────────────────────────────
    if df.isnull().sum().sum() > 0:
        fig, ax = plt.subplots(figsize=(max(8, len(df.columns) * 0.6), 4))
        _base_style(fig, ax)
        missing_matrix = df.isnull().T
        sns.heatmap(missing_matrix, ax=ax, cmap="RdYlGn_r",
                    cbar_kws={"label": "Missing"},
                    yticklabels=True, xticklabels=False,
                    linewidths=0.3, linecolor=GRID_COLOR)
        ax.set_title("Missing Values Heatmap", fontsize=13, fontweight="bold", pad=10)
        ax.tick_params(colors=TEXT_COLOR)
        charts.append({"title": "Missing Values Heatmap", "img": _fig_to_b64(fig)})

    # ── 2. Distribution Plots (numeric) ───────────────────────────────────────
    if num_cols:
        n = len(num_cols)
        cols_per_row = 3
        rows = (n + cols_per_row - 1) // cols_per_row
        fig, axes = plt.subplots(rows, cols_per_row,
                                 figsize=(cols_per_row * 4.5, rows * 3.5))
        fig.patch.set_facecolor(BG_COLOR)
        axes_flat = np.array(axes).flatten()
        for i, col in enumerate(num_cols):
            ax = axes_flat[i]
            _base_style(fig, ax)
            data = df[col].dropna()
            ax.hist(data, bins=30, color=PALETTE[i % len(PALETTE)],
                    alpha=0.85, edgecolor="none")
            # KDE overlay
            try:
                from scipy.stats import gaussian_kde
                kde_x = np.linspace(data.min(), data.max(), 200)
                kde   = gaussian_kde(data)
                ax2   = ax.twinx()
                ax2.plot(kde_x, kde(kde_x), color="white", lw=1.5, alpha=0.7)
                ax2.set_yticks([])
                ax2.set_facecolor(CARD_COLOR)
            except Exception:
                pass
            ax.set_title(col, fontsize=10, fontweight="bold")
            ax.set_xlabel("")
        for j in range(i + 1, len(axes_flat)):
            axes_flat[j].set_visible(False)
        fig.suptitle("Numeric Distributions", fontsize=14, color=TEXT_COLOR,
                     fontweight="bold", y=1.01)
        fig.tight_layout()
        charts.append({"title": "Numeric Distributions", "img": _fig_to_b64(fig)})

    # ── 3. Box Plots (outlier view) ────────────────────────────────────────────
    if num_cols:
        fig, ax = plt.subplots(figsize=(max(8, len(num_cols) * 1.2), 5))
        _base_style(fig, ax)
        df_norm = df[num_cols].copy()
        for col in df_norm.columns:
            r = df_norm[col].max() - df_norm[col].min()
            if r > 0:
                df_norm[col] = (df_norm[col] - df_norm[col].min()) / r
        bp = ax.boxplot(
            [df_norm[c].dropna().values for c in num_cols],
            patch_artist=True,
            labels=num_cols,
            medianprops=dict(color="white", linewidth=2),
            whiskerprops=dict(color=TEXT_COLOR),
            capprops=dict(color=TEXT_COLOR),
            flierprops=dict(markerfacecolor=PALETTE[5], marker="o",
                            markersize=3, alpha=0.5),
        )
        for patch, color in zip(bp["boxes"], PALETTE * 10):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)
        ax.set_title("Box Plots – Normalised (0-1 Scale)", fontsize=13,
                     fontweight="bold")
        ax.set_xticklabels(num_cols, rotation=35, ha="right", fontsize=9)
        charts.append({"title": "Box Plots (Outlier View)", "img": _fig_to_b64(fig)})

    # ── 4. Correlation Heatmap ─────────────────────────────────────────────────
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        size = max(6, min(14, len(num_cols)))
        fig, ax = plt.subplots(figsize=(size, size * 0.8))
        _base_style(fig, ax)
        mask = np.triu(np.ones_like(corr, dtype=bool))
        cmap = sns.diverging_palette(250, 10, as_cmap=True)
        sns.heatmap(corr, ax=ax, mask=mask, cmap=cmap,
                    annot=True, fmt=".2f", annot_kws={"size": 8},
                    linewidths=0.5, linecolor=GRID_COLOR,
                    vmin=-1, vmax=1,
                    cbar_kws={"shrink": 0.8})
        ax.set_title("Correlation Heatmap", fontsize=13, fontweight="bold", pad=12)
        ax.tick_params(axis="x", rotation=35)
        charts.append({"title": "Correlation Heatmap", "img": _fig_to_b64(fig)})

    # ── 5. Categorical Bar Charts ──────────────────────────────────────────────
    for col in cat_cols[:4]:
        vc = df[col].value_counts().head(12)
        if len(vc) < 2:
            continue
        fig, ax = plt.subplots(figsize=(8, 4))
        _base_style(fig, ax)
        bars = ax.barh(vc.index.astype(str)[::-1],
                       vc.values[::-1],
                       color=[PALETTE[i % len(PALETTE)] for i in range(len(vc))],
                       edgecolor="none", height=0.65)
        for bar, val in zip(bars, vc.values[::-1]):
            ax.text(bar.get_width() + vc.values.max() * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=8, color=TEXT_COLOR)
        ax.set_title(f"'{col}' – Value Counts (Top {len(vc)})",
                     fontsize=12, fontweight="bold")
        ax.set_xlabel("Count")
        ax.set_xlim(0, vc.values.max() * 1.18)
        charts.append({"title": f"'{col}' Value Counts", "img": _fig_to_b64(fig)})

    # ── 6. Pairplot / Scatter Matrix (up to 5 numeric cols) ───────────────────
    if 2 <= len(num_cols) <= 6:
        sample = df[num_cols].dropna().sample(min(500, len(df)), random_state=42)
        g = sns.pairplot(sample, diag_kind="kde",
                         plot_kws={"alpha": 0.4, "s": 15,
                                   "color": PALETTE[0]},
                         diag_kws={"color": PALETTE[2], "fill": True})
        g.fig.patch.set_facecolor(BG_COLOR)
        for ax in g.axes.flatten():
            ax.set_facecolor(CARD_COLOR)
            ax.tick_params(colors=TEXT_COLOR, labelsize=7)
            ax.xaxis.label.set_color(TEXT_COLOR)
            ax.yaxis.label.set_color(TEXT_COLOR)
            for sp in ax.spines.values():
                sp.set_edgecolor(GRID_COLOR)
        g.fig.suptitle("Scatter Matrix", fontsize=14, color=TEXT_COLOR,
                       fontweight="bold", y=1.01)
        charts.append({"title": "Scatter Matrix", "img": _fig_to_b64(g.fig)})

    return charts
