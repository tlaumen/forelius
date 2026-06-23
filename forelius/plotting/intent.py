from __future__ import annotations

from baml_client import types as baml_types

from forelius.plotting.data import ValidatedColumn, ValidatedDataset, count_finite_pairs
from forelius.plotting.errors import PlotIntentError

_MAX_AXIS_LABEL_LENGTH = 120
_MAX_CAPTION_LENGTH = 300


def validate_plot_intent(
    intent: baml_types.XYPlotIntent,
    dataset: ValidatedDataset,
) -> baml_types.XYPlotIntent:
    columns_by_name = {column.name: column for column in dataset.columns}

    x_column = _require_column(intent.x, columns_by_name, "x")
    y_column = _require_column(intent.y, columns_by_name, "y")
    _require_numeric_column(x_column, "x")
    _require_numeric_column(y_column, "y")
    _validate_numeric_lengths(x_column, y_column)
    _validate_finite_pairs(x_column, y_column)
    _validate_visible_style(intent)
    _validate_axis_limit(intent.options.x_lim, "x_lim")
    _validate_axis_limit(intent.options.y_lim, "y_lim")
    _validate_text_lengths(intent)

    return intent


def _require_column(
    name: str,
    columns_by_name: dict[str, ValidatedColumn],
    axis_name: str,
) -> ValidatedColumn:
    try:
        return columns_by_name[name]
    except KeyError as exc:
        raise PlotIntentError(f"Intent {axis_name} column does not exist: {name!r}") from exc


def _require_numeric_column(column: ValidatedColumn, axis_name: str) -> None:
    if column.data_type != "number" or column.numeric_values is None:
        raise PlotIntentError(f"Intent {axis_name} column must be numeric: {column.name!r}")


def _validate_numeric_lengths(x_column: ValidatedColumn, y_column: ValidatedColumn) -> None:
    if x_column.numeric_values is None or y_column.numeric_values is None:
        raise PlotIntentError("Intent columns must contain parsed numeric values")
    if len(x_column.numeric_values) != len(y_column.numeric_values):
        raise PlotIntentError("Intent x and y columns must have equal lengths")


def _validate_finite_pairs(x_column: ValidatedColumn, y_column: ValidatedColumn) -> None:
    if x_column.numeric_values is None or y_column.numeric_values is None:
        raise PlotIntentError("Intent columns must contain parsed numeric values")
    finite_pairs = count_finite_pairs(x_column.numeric_values, y_column.numeric_values)
    if finite_pairs < 2:
        raise PlotIntentError("Intent x and y columns must have at least two finite pairs")


def _validate_visible_style(intent: baml_types.XYPlotIntent) -> None:
    if (
        intent.options.line_style is baml_types.PlotLineStyle.NONE
        and intent.options.marker is baml_types.PlotMarker.NONE
    ):
        raise PlotIntentError("Intent line_style and marker cannot both be NONE")


def _validate_axis_limit(limit: baml_types.AxisLimit | None, field_name: str) -> None:
    if limit is None:
        return
    if limit.min is None and limit.max is None:
        raise PlotIntentError(f"Intent {field_name} must define min, max, or both")
    if limit.min is not None and limit.max is not None and limit.min >= limit.max:
        raise PlotIntentError(f"Intent {field_name} min must be less than max")


def _validate_text_lengths(intent: baml_types.XYPlotIntent) -> None:
    _validate_optional_text_length(intent.options.title, "title", _MAX_AXIS_LABEL_LENGTH)
    _validate_optional_text_length(intent.options.x_label, "x_label", _MAX_AXIS_LABEL_LENGTH)
    _validate_optional_text_length(intent.options.y_label, "y_label", _MAX_AXIS_LABEL_LENGTH)
    if len(intent.caption) > _MAX_CAPTION_LENGTH:
        raise PlotIntentError("Intent caption is too long")


def _validate_optional_text_length(value: str | None, field_name: str, max_length: int) -> None:
    if value is not None and len(value) > max_length:
        raise PlotIntentError(f"Intent {field_name} is too long")
