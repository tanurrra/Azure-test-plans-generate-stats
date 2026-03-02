"""Generate PNG chart images from automation statistics CSV for Confluence upload."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np

from generate_charts import (
    create_current_snapshot,
    create_module_pct_trends,
    create_module_trends,
    create_overall_summary,
    load_and_prepare_data,
)

# Match Excel dashboard colors
COLORS_AUTOMATED_PLANNED_NOT = ["#70AD47", "#4472C4", "#808080"]
COLORS_MODULES = [
    "#5B9BD5", "#ED7D31", "#A5A5A5", "#FFC000", "#4472C4",
    "#70AD47", "#255E91", "#9E480E", "#636363", "#997300",
    "#264478", "#43682B", "#FF5050", "#9933FF", "#00B0F0",
    "#92D050",
]


def _fig_style(ax: plt.Axes) -> None:
    """Apply consistent style: left/bottom margin, grid."""
    ax.set_axisbelow(True)
    ax.grid(True, axis="both", alpha=0.3)
    plt.tight_layout()


def save_stacked_area(df_summary: object, out_path: str, title: str) -> None:
    """Stacked area: automated, planned, not_automated over dates."""
    fig, ax = plt.subplots(figsize=(10, 5))
    dates = df_summary["date"].tolist()
    x = np.arange(len(dates))
    width = 0.8
    ax.fill_between(x, 0, df_summary["automated"], label="Automated", color=COLORS_AUTOMATED_PLANNED_NOT[0])
    ax.fill_between(
        x,
        df_summary["automated"],
        df_summary["automated"] + df_summary["planned"],
        label="Planned",
        color=COLORS_AUTOMATED_PLANNED_NOT[1],
    )
    ax.fill_between(
        x,
        df_summary["automated"] + df_summary["planned"],
        df_summary["total_cases"],
        label="Not Automated",
        color=COLORS_AUTOMATED_PLANNED_NOT[2],
    )
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    ax.set_ylabel("Number of Tests")
    ax.set_xlabel("Date")
    ax.set_title(title)
    ax.legend(loc="upper left")
    _fig_style(ax)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_overall_pct_line(df_summary: object, out_path: str, title: str) -> None:
    """Line chart: overall automation % over time."""
    fig, ax = plt.subplots(figsize=(10, 5))
    dates = df_summary["date"].tolist()
    pct = df_summary["automation_pct"].tolist()
    x = np.arange(len(dates))
    ax.plot(x, pct, color="#70AD47", marker="o", markersize=6, linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    ax.set_ylabel("Automation %")
    ax.set_xlabel("Date")
    ax.set_title(title)
    ax.set_ylim(0, 100)
    _fig_style(ax)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_module_trends_stacked(df_trends: object, out_path: str, title: str) -> None:
    """Stacked column: automated count per module per date."""
    fig, ax = plt.subplots(figsize=(12, 5))
    dates = df_trends["date"].tolist()
    x = np.arange(len(dates))
    width = 0.75
    module_cols = [c for c in df_trends.columns if c != "date"]
    colors = [COLORS_MODULES[i % len(COLORS_MODULES)] for i in range(len(module_cols))]
    bottom = np.zeros(len(dates))
    for i, col in enumerate(module_cols):
        vals = df_trends[col].values
        ax.bar(x, vals, width=width, bottom=bottom, label=col, color=colors[i])
        bottom = bottom + vals
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    ax.set_ylabel("Automated Tests")
    ax.set_xlabel("Date")
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=7)
    _fig_style(ax)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_module_pct_line(df_pct: object, out_path: str, title: str) -> None:
    """Line chart: automation % per module over time."""
    fig, ax = plt.subplots(figsize=(12, 5))
    dates = df_pct["date"].tolist()
    module_cols = [c for c in df_pct.columns if c != "date"]
    x = np.arange(len(dates))
    for i, col in enumerate(module_cols):
        color = COLORS_MODULES[i % len(COLORS_MODULES)]
        ax.plot(x, df_pct[col].values, marker="o", markersize=4, label=col, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right")
    ax.set_ylabel("Automation %")
    ax.set_xlabel("Date")
    ax.set_title(title)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper left", fontsize=7)
    _fig_style(ax)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_current_status_hbar(df_snapshot: object, out_path: str, title: str) -> None:
    """Horizontal stacked bar: current week by module."""
    fig, ax = plt.subplots(figsize=(10, max(5, len(df_snapshot) * 0.35)))
    modules = df_snapshot["root_suite_name"].tolist()
    y = np.arange(len(modules))
    height = 0.7
    left = np.zeros(len(modules))
    for i, col in enumerate(["automated", "planned", "not_automated"]):
        vals = df_snapshot[col].values
        ax.barh(y, vals, height=height, left=left, label=col.replace("_", " ").title(), color=COLORS_AUTOMATED_PLANNED_NOT[i])
        left = left + vals
    ax.set_yticks(y)
    ax.set_yticklabels(modules)
    ax.set_xlabel("Number of Tests")
    ax.set_title(title)
    ax.legend(loc="lower right")
    _fig_style(ax)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_plan_images(csv_path: str, output_dir: str, prefix: str, plan_name: str) -> None:
    """Generate all five PNGs for one plan (regression or release)."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    df = load_and_prepare_data(csv_path)
    overall_summary = create_overall_summary(df)
    module_trends = create_module_trends(df)
    module_pct_trends = create_module_pct_trends(df)
    current_snapshot = create_current_snapshot(df)

    save_stacked_area(
        overall_summary,
        os.path.join(output_dir, f"{prefix}_overall_progress.png"),
        f"{plan_name} - Overall Automation Progress",
    )
    save_overall_pct_line(
        overall_summary,
        os.path.join(output_dir, f"{prefix}_overall_pct.png"),
        f"{plan_name} - Overall Automation %",
    )
    save_module_trends_stacked(
        module_trends,
        os.path.join(output_dir, f"{prefix}_module_trends.png"),
        f"{plan_name} - Automation by Module",
    )
    save_module_pct_line(
        module_pct_trends,
        os.path.join(output_dir, f"{prefix}_module_pct_trends.png"),
        f"{plan_name} - Automation % by Module",
    )
    save_current_status_hbar(
        current_snapshot,
        os.path.join(output_dir, f"{prefix}_current_status.png"),
        f"{plan_name} - Current Status by Module",
    )


def main() -> None:
    """Generate PNGs for regression and release plans into chart_images/."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "chart_images")

    regression_csv = os.path.join(script_dir, "automation_stats_regression.csv")
    release_csv = os.path.join(script_dir, "automation_stats_release.csv")

    if os.path.exists(regression_csv):
        generate_plan_images(regression_csv, output_dir, "regression", "E2E - V5 Regression")
        print(f"Generated regression charts in {output_dir}")

    if os.path.exists(release_csv):
        generate_plan_images(release_csv, output_dir, "release", "E2E - Release")
        print(f"Generated release charts in {output_dir}")


if __name__ == "__main__":
    main()
