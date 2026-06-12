#!/usr/bin/env python3
"""Generate zeroLET runtime plots from an evaluation CSV file."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


MARKERS = ("o", "s", "^", "D", "v", "P", "d", "X", "x")
COLORS = plt.colormaps["tab10"].colors
FIGURE_SIZE = (3.5, 2.8)
OUTPUT_DPI = 300
TITLE_SIZE = 6
LABEL_SIZE = 6
TICK_SIZE = 6
LEGEND_SIZE = 6
MARKER_SIZE = 2
FILENAME_PATTERN = re.compile(
    r"^data_zero_let_RC_n(?P<num_chains>\d+)_(?P<num_repeats>\d+)_"
    r"(?P<seed>-?\d+)_(?P<timestamp>[^.]+)\.csv$"
)


def output_stem(csv_path: Path, plot_kind: str) -> str:
    match = FILENAME_PATTERN.match(csv_path.name)
    if match:
        metadata = match.groupdict()
        return (
            f"zero_let_{plot_kind}_n{metadata['num_chains']}_"
            f"{metadata['num_repeats']}_{metadata['seed']}_"
            f"{metadata['timestamp']}"
        )
    return f"{csv_path.stem}_{plot_kind}"


def load_results(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    required = {"n", "C", "R", "R/C"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")

    data = frame.loc[:, ["n", "C", "R", "R/C"]].copy()
    for column in data.columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna()
    data = data[(data["C"] > 0) & (data["R"] > 0) & (data["R/C"] > 0)]
    if data.empty:
        raise ValueError("CSV contains no positive numeric plotting data")
    return data


def create_plot(
    data: pd.DataFrame,
    y_column: str,
    title: str,
    y_label: str,
    output_path: Path,
) -> None:
    figure, axes = plt.subplots(figsize=FIGURE_SIZE)

    for index, n_value in enumerate(sorted(data["n"].unique())):
        subset = data[data["n"] == n_value]
        axes.scatter(
            subset["C"],
            subset[y_column],
            label=f"n={int(n_value)}",
            marker=MARKERS[index % len(MARKERS)],
            color=COLORS[index % len(COLORS)],
            s=MARKER_SIZE,
            linewidths=0.8,
        )

    axes.set_xscale("log")
    axes.set_yscale("log")
    axes.set_xlabel("Complexity (C)", fontsize=LABEL_SIZE)
    axes.set_ylabel(y_label, fontsize=LABEL_SIZE)
    axes.set_title(title, fontsize=TITLE_SIZE)
    axes.tick_params(axis="both", which="major", labelsize=TICK_SIZE)
    axes.tick_params(axis="both", which="minor", labelsize=TICK_SIZE)
    axes.grid(True, which="major", color="#d6d6d6", linewidth=0.5)

    axes.legend(
        title="Task chain length",
        loc="best",
        frameon=True,
        fontsize=LEGEND_SIZE,
        title_fontsize=LEGEND_SIZE,
        markerscale=0.85,
        borderpad=0.5,
        labelspacing=0.35,
        handletextpad=0.5,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout(pad=0.4)
    figure.savefig(
        output_path,
        dpi=OUTPUT_DPI,
        facecolor="white",
        bbox_inches="tight",
        pad_inches=0.02,
    )
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read a zeroLET CSV file and generate Runtime and R/C PNG plots."
    )
    parser.add_argument("csv_file", type=Path, help="zeroLET evaluation CSV file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="output directory; defaults to the CSV file directory",
    )
    args = parser.parse_args()

    csv_path = args.csv_file.resolve()
    if not csv_path.is_file():
        parser.error(f"CSV file does not exist: {csv_path}")

    output_dir = args.output_dir.resolve() if args.output_dir else csv_path.parent
    data = load_results(csv_path)
    runtime_path = output_dir / f"{output_stem(csv_path, 'Runtime')}.png"
    normalized_path = output_dir / f"{output_stem(csv_path, 'RC')}.png"

    create_plot(
        data,
        "R",
        "Runtime (R) over Complexity (C)",
        "Runtime (R) [seconds]",
        runtime_path,
    )
    create_plot(
        data,
        "R/C",
        "Normalized Runtime (R/C)",
        "R / C",
        normalized_path,
    )

    print(f"Runtime plot saved to {runtime_path}")
    print(f"Normalized runtime plot saved to {normalized_path}")
    return 0


if __name__ == "__main__":
    plt.rcParams["font.family"] = "Arial"
    raise SystemExit(main())
