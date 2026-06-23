from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from baml_client import types as baml_types
from matplotlib.colors import is_color_like

from forelius.elements import Plot
from forelius.plotting.data import ValidatedColumn, ValidatedDataset
from forelius.plotting.errors import PlotRenderingError
from forelius.plotting.intent import validate_plot_intent

LINESTYLE_MAP = {
    baml_types.PlotLineStyle.SOLID: "-",
    baml_types.PlotLineStyle.DASHED: "--",
    baml_types.PlotLineStyle.DOTTED: ":",
    baml_types.PlotLineStyle.DASHDOT: "-.",
    baml_types.PlotLineStyle.NONE: "",
}

MARKER_MAP = {
    baml_types.PlotMarker.NONE: "",
    baml_types.PlotMarker.CIRCLE: "o",
    baml_types.PlotMarker.SQUARE: "s",
    baml_types.PlotMarker.TRIANGLE: "^",
    baml_types.PlotMarker.DIAMOND: "D",
    baml_types.PlotMarker.CROSS: "x",
}

_SAFE_STEM_PATTERN = re.compile(r"[^a-z0-9_-]+")


def render_xy_plot(
    dataset: ValidatedDataset,
    intent: baml_types.XYPlotIntent,
    output_dir: Path,
    filename_stem: str | None = None,
    overwrite: bool = False,
) -> Plot:
    validate_plot_intent(intent, dataset)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        output_path = output_dir / f"{_safe_filename_stem(filename_stem)}.png"
    else:
        output_path = _non_overwriting_png_path(output_dir, filename_stem)

    x_column = _column_by_name(dataset, intent.x)
    y_column = _column_by_name(dataset, intent.y)
    if x_column.numeric_values is None or y_column.numeric_values is None:
        raise PlotRenderingError("Selected columns must contain numeric values")

    fig, ax = plt.subplots()
    try:
        plot_kwargs = {
            "linestyle": LINESTYLE_MAP[intent.options.line_style],
            "marker": MARKER_MAP[intent.options.marker],
        }
        if intent.options.color is not None:
            if not is_color_like(intent.options.color):
                raise PlotRenderingError(f"Invalid matplotlib color: {intent.options.color!r}")
            plot_kwargs["color"] = intent.options.color

        ax.plot(x_column.numeric_values, y_column.numeric_values, **plot_kwargs)
        _apply_options(ax, intent)
        fig.tight_layout()
        fig.savefig(output_path, format="png")
    except PlotRenderingError:
        raise
    except Exception as exc:
        raise PlotRenderingError("Failed to render XY plot") from exc
    finally:
        plt.close(fig)

    return Plot(caption=intent.caption, path=output_path)


def _apply_options(ax, intent: baml_types.XYPlotIntent) -> None:
    options = intent.options
    if options.title:
        ax.set_title(options.title)
    if options.x_label:
        ax.set_xlabel(options.x_label)
    if options.y_label:
        ax.set_ylabel(options.y_label)
    if options.x_lim is not None:
        current_min, current_max = ax.get_xlim()
        ax.set_xlim(
            options.x_lim.min if options.x_lim.min is not None else current_min,
            options.x_lim.max if options.x_lim.max is not None else current_max,
        )
    if options.y_lim is not None:
        current_min, current_max = ax.get_ylim()
        ax.set_ylim(
            options.y_lim.min if options.y_lim.min is not None else current_min,
            options.y_lim.max if options.y_lim.max is not None else current_max,
        )
    if options.grid is baml_types.PlotGrid.MAJOR:
        ax.grid(True, which="major")
    elif options.grid is baml_types.PlotGrid.BOTH:
        ax.grid(True, which="both")
    if options.invert_x:
        ax.invert_xaxis()
    if options.invert_y:
        ax.invert_yaxis()


def _column_by_name(dataset: ValidatedDataset, name: str) -> ValidatedColumn:
    for column in dataset.columns:
        if column.name == name:
            return column
    raise PlotRenderingError(f"Column not found after intent validation: {name!r}")


def _non_overwriting_png_path(output_dir: Path, filename_stem: str | None) -> Path:
    safe_stem = _safe_filename_stem(filename_stem)
    candidate = output_dir / f"{safe_stem}.png"
    if not candidate.exists():
        return candidate

    suffix = 2
    while True:
        candidate = output_dir / f"{safe_stem}_{suffix}.png"
        if not candidate.exists():
            return candidate
        suffix += 1


def _safe_filename_stem(filename_stem: str | None) -> str:
    if filename_stem is None:
        return f"plot_{uuid4().hex}"

    normalized = filename_stem.strip().lower()
    normalized = _SAFE_STEM_PATTERN.sub("_", normalized)
    normalized = normalized.strip("_")
    if not normalized:
        return f"plot_{uuid4().hex}"
    return normalized
