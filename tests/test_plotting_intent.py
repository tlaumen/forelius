import math

import pytest
from baml_client import types as baml_types

from forelius.plotting import (
    ExtractedColumn,
    ExtractedDataset,
    PlotIntentError,
    validate_extracted_dataset,
    validate_plot_intent,
)
from forelius.plotting.data import ValidatedDataset


def make_dataset(columns: list[ExtractedColumn] | None = None) -> ValidatedDataset:
    extracted = ExtractedDataset(
        data_start_line=1,
        data_end_line=4,
        confidence="high",
        columns=columns
        or [
            ExtractedColumn(
                name="Depth",
                unit="m",
                data_type="number",
                values=["0", "1", "2"],
            ),
            ExtractedColumn(
                name="Settlement",
                unit="mm",
                data_type="number",
                values=["0", "10", "20"],
            ),
        ],
    )
    return validate_extracted_dataset(extracted)


def make_intent(**overrides) -> baml_types.XYPlotIntent:
    options = overrides.pop(
        "options",
        baml_types.XYPlotOptions(
            title="Settlement profile",
            x_label="Depth (m)",
            y_label="Settlement (mm)",
            x_lim=None,
            y_lim=None,
            grid=baml_types.PlotGrid.MAJOR,
            line_style=baml_types.PlotLineStyle.SOLID,
            marker=baml_types.PlotMarker.NONE,
            color=None,
            invert_x=False,
            invert_y=False,
        ),
    )
    values = {
        "x": "Depth",
        "y": "Settlement",
        "caption": "Settlement versus depth.",
        "options": options,
    }
    values.update(overrides)
    return baml_types.XYPlotIntent(**values)


def test_validate_plot_intent_accepts_valid_generated_baml_intent() -> None:
    dataset = make_dataset()
    intent = make_intent()

    validated = validate_plot_intent(intent, dataset)

    assert validated is intent


@pytest.mark.parametrize(("field", "value"), [("x", "Missing"), ("y", "Missing")])
def test_validate_plot_intent_rejects_missing_columns(field: str, value: str) -> None:
    with pytest.raises(PlotIntentError, match="does not exist"):
        validate_plot_intent(make_intent(**{field: value}), make_dataset())


def test_validate_plot_intent_rejects_non_numeric_columns() -> None:
    dataset = make_dataset(
        [
            ExtractedColumn(name="Load case", data_type="category", values=["A", "B"]),
            ExtractedColumn(name="Force", data_type="number", values=["10", "20"]),
        ]
    )

    with pytest.raises(PlotIntentError, match="must be numeric"):
        validate_plot_intent(make_intent(x="Load case", y="Force"), dataset)


def test_validate_plot_intent_rejects_fewer_than_two_finite_pairs() -> None:
    dataset = make_dataset(
        [
            ExtractedColumn(name="X", data_type="number", values=["1", "-", "-"]),
            ExtractedColumn(name="Y", data_type="number", values=["2", "3", "-"]),
        ]
    )

    with pytest.raises(PlotIntentError, match="two finite pairs"):
        validate_plot_intent(make_intent(x="X", y="Y"), dataset)


def test_validate_plot_intent_rejects_invisible_plot_style() -> None:
    options = make_intent().options.model_copy(
        update={
            "line_style": baml_types.PlotLineStyle.NONE,
            "marker": baml_types.PlotMarker.NONE,
        }
    )

    with pytest.raises(PlotIntentError, match="cannot both be NONE"):
        validate_plot_intent(make_intent(options=options), make_dataset())


@pytest.mark.parametrize(
    "options",
    [
        make_intent().options.model_copy(
            update={"x_lim": baml_types.AxisLimit(min=2.0, max=2.0)}
        ),
        make_intent().options.model_copy(
            update={"y_lim": baml_types.AxisLimit(min=5.0, max=4.0)}
        ),
    ],
)
def test_validate_plot_intent_rejects_non_increasing_axis_limits(
    options: baml_types.XYPlotOptions,
) -> None:
    with pytest.raises(PlotIntentError, match="min must be less than max"):
        validate_plot_intent(make_intent(options=options), make_dataset())


def test_validate_plot_intent_accepts_partial_axis_limits() -> None:
    options = make_intent().options.model_copy(
        update={
            "x_lim": baml_types.AxisLimit(min=0.0, max=None),
            "y_lim": baml_types.AxisLimit(min=None, max=25.0),
        }
    )

    assert validate_plot_intent(make_intent(options=options), make_dataset())


def test_validate_plot_intent_rejects_empty_axis_limit_object() -> None:
    options = make_intent().options.model_copy(
        update={"x_lim": baml_types.AxisLimit(min=None, max=None)}
    )

    with pytest.raises(PlotIntentError, match="must define min, max, or both"):
        validate_plot_intent(make_intent(options=options), make_dataset())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("caption", "x" * 301, "caption"),
        ("title", "x" * 121, "title"),
        ("x_label", "x" * 121, "x_label"),
        ("y_label", "x" * 121, "y_label"),
    ],
)
def test_validate_plot_intent_rejects_overlong_text_fields(
    field: str,
    value: str,
    message: str,
) -> None:
    if field == "caption":
        intent = make_intent(caption=value)
    else:
        intent = make_intent(options=make_intent().options.model_copy(update={field: value}))

    with pytest.raises(PlotIntentError, match=message):
        validate_plot_intent(intent, make_dataset())


def test_validate_plot_intent_accepts_nan_values_when_two_finite_pairs_remain() -> None:
    dataset = make_dataset(
        [
            ExtractedColumn(name="X", data_type="number", values=["1", "-", "3"]),
            ExtractedColumn(name="Y", data_type="number", values=["2", "3", "4"]),
        ]
    )

    assert math.isnan(dataset.columns[0].numeric_values[1])
    assert validate_plot_intent(make_intent(x="X", y="Y"), dataset)
