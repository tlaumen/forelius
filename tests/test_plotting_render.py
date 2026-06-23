from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from baml_client import types as baml_types

from forelius.elements import Plot
from forelius.plotting import (
    ExtractedColumn,
    ExtractedDataset,
    PlotRenderingError,
    render_xy_plot,
    validate_extracted_dataset,
)
from forelius.plotting.data import ValidatedDataset


def make_dataset(columns: list[ExtractedColumn] | None = None) -> ValidatedDataset:
    extracted = ExtractedDataset(
        data_start_line=1,
        data_end_line=4,
        confidence="high",
        columns=columns
        or [
            ExtractedColumn(name="X", unit="m", data_type="number", values=["0", "1", "2"]),
            ExtractedColumn(name="Y", unit="mm", data_type="number", values=["0", "10", "-"]),
        ],
    )
    return validate_extracted_dataset(extracted)


def make_intent(**overrides) -> baml_types.XYPlotIntent:
    options = overrides.pop(
        "options",
        baml_types.XYPlotOptions(
            title="Test plot",
            x_label="X (m)",
            y_label="Y (mm)",
            x_lim=None,
            y_lim=None,
            grid=baml_types.PlotGrid.MAJOR,
            line_style=baml_types.PlotLineStyle.SOLID,
            marker=baml_types.PlotMarker.CIRCLE,
            color=None,
            invert_x=False,
            invert_y=False,
        ),
    )
    values = {
        "x": "X",
        "y": "Y",
        "caption": "Rendered test plot.",
        "options": options,
    }
    values.update(overrides)
    return baml_types.XYPlotIntent(**values)


def test_render_xy_plot_writes_png_and_returns_plot(tmp_path: Path) -> None:
    plot = render_xy_plot(make_dataset(), make_intent(), tmp_path, "result")

    assert isinstance(plot, Plot)
    assert plot.caption == "Rendered test plot."
    assert plot.path.exists()
    assert plot.path.suffix == ".png"
    assert plot.path.read_bytes().startswith(b"\x89PNG")


def test_render_xy_plot_creates_output_directory(tmp_path: Path) -> None:
    output_dir = tmp_path / "nested" / "plots"

    plot = render_xy_plot(make_dataset(), make_intent(), output_dir, "result")

    assert output_dir.exists()
    assert plot.path.parent == output_dir


def test_render_xy_plot_sanitizes_filename_stem(tmp_path: Path) -> None:
    plot = render_xy_plot(make_dataset(), make_intent(), tmp_path, "My plot: settlement!")

    assert plot.path.name == "my_plot_settlement.png"


def test_render_xy_plot_generates_uuid_filename_when_stem_is_missing(tmp_path: Path) -> None:
    plot = render_xy_plot(make_dataset(), make_intent(), tmp_path)

    assert plot.path.name.startswith("plot_")
    assert plot.path.suffix == ".png"


def test_render_xy_plot_does_not_overwrite_existing_files(tmp_path: Path) -> None:
    first = render_xy_plot(make_dataset(), make_intent(), tmp_path, "plot")
    second = render_xy_plot(make_dataset(), make_intent(), tmp_path, "plot")

    assert first.path.name == "plot.png"
    assert second.path.name == "plot_2.png"
    assert first.path.read_bytes().startswith(b"\x89PNG")
    assert second.path.read_bytes().startswith(b"\x89PNG")


def test_render_xy_plot_closes_figures_after_rendering(tmp_path: Path) -> None:
    before = set(plt.get_fignums())

    render_xy_plot(make_dataset(), make_intent(), tmp_path, "plot")

    assert set(plt.get_fignums()) == before


def test_render_xy_plot_accepts_supported_matplotlib_color(tmp_path: Path) -> None:
    options = make_intent().options.model_copy(update={"color": "tab:blue"})

    plot = render_xy_plot(make_dataset(), make_intent(options=options), tmp_path, "blue")

    assert plot.path.exists()


def test_render_xy_plot_rejects_invalid_color(tmp_path: Path) -> None:
    options = make_intent().options.model_copy(update={"color": "not-a-color"})

    with pytest.raises(PlotRenderingError, match="Invalid matplotlib color"):
        render_xy_plot(make_dataset(), make_intent(options=options), tmp_path, "bad")


def test_render_xy_plot_validates_intent_before_rendering(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        render_xy_plot(make_dataset(), make_intent(y="Missing"), tmp_path, "bad")


def test_render_xy_plot_applies_axis_limits_and_inversion(tmp_path: Path) -> None:
    options = make_intent().options.model_copy(
        update={
            "x_lim": baml_types.AxisLimit(min=0.0, max=2.0),
            "y_lim": baml_types.AxisLimit(min=-1.0, max=11.0),
            "grid": baml_types.PlotGrid.BOTH,
            "invert_x": True,
            "invert_y": True,
        }
    )

    plot = render_xy_plot(make_dataset(), make_intent(options=options), tmp_path, "limits")

    assert plot.path.exists()


def test_render_xy_plot_accepts_partial_axis_limits(tmp_path: Path) -> None:
    options = make_intent().options.model_copy(
        update={
            "x_lim": baml_types.AxisLimit(min=0.0, max=None),
            "y_lim": baml_types.AxisLimit(min=0.0, max=None),
        }
    )

    plot = render_xy_plot(make_dataset(), make_intent(options=options), tmp_path, "partial_limits")

    assert plot.path.exists()
