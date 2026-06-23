from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import BaseModel, Field

from forelius.plotting.errors import PlotDataError

DataType = Literal["number", "text", "category", "date"]
Confidence = Literal["low", "medium", "high"]

_MISSING_OR_NONFINITE_TOKENS = {
    "",
    "-",
    "—",
    "n/a",
    "na",
    "null",
    "none",
    "geen",
    "nan",
    "+nan",
    "-nan",
    "inf",
    "+inf",
    "-inf",
    "infinity",
    "+infinity",
    "-infinity",
}
_NUMERIC_CHARS_PATTERN = re.compile(r"^[+-]?[0-9][0-9.,]*$")


class ExtractedColumn(BaseModel):
    name: str
    unit: str | None = None
    data_type: DataType
    values: list[str]


class ExtractedDataset(BaseModel):
    data_start_line: int
    data_end_line: int
    columns: list[ExtractedColumn]
    confidence: Confidence
    assumptions: list[str] = Field(default_factory=list)


class ValidatedColumn(BaseModel):
    name: str
    unit: str | None = None
    data_type: DataType
    values: list[str]
    numeric_values: list[float] | None = None


class ValidatedDataset(BaseModel):
    source: ExtractedDataset
    columns: list[ValidatedColumn]
    assumptions: list[str] = Field(default_factory=list)


class DatasetColumnMetadata(BaseModel):
    name: str
    unit: str | None = None
    data_type: DataType


class DatasetMetadata(BaseModel):
    columns: list[DatasetColumnMetadata]
    assumptions: list[str] = Field(default_factory=list)


def number_input_lines(text: str) -> str:
    return "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(text.splitlines(), start=1)
    )


def parse_numeric_value(value: str) -> float:
    stripped = value.strip()
    if stripped.lower() in _MISSING_OR_NONFINITE_TOKENS:
        return float("nan")

    if not _NUMERIC_CHARS_PATTERN.fullmatch(stripped):
        raise PlotDataError(f"Invalid numeric value: {value!r}")

    sign = ""
    unsigned = stripped
    if unsigned[0] in "+-":
        sign = unsigned[0]
        unsigned = unsigned[1:]

    if unsigned.count(".") and unsigned.count(","):
        decimal_separator = "." if unsigned.rfind(".") > unsigned.rfind(",") else ","
        thousands_separator = "," if decimal_separator == "." else "."
        normalized = unsigned.replace(thousands_separator, "")
        normalized = normalized.replace(decimal_separator, ".")
    elif "." in unsigned or "," in unsigned:
        separator = "." if "." in unsigned else ","
        parts = unsigned.split(separator)
        if _is_repeated_thousands_grouping(parts):
            normalized = "".join(parts)
        elif len(parts) == 2 and parts[0] and parts[1]:
            normalized = f"{parts[0]}.{parts[1]}"
        else:
            raise PlotDataError(f"Invalid numeric value: {value!r}")
    else:
        normalized = unsigned

    try:
        parsed = float(f"{sign}{normalized}")
    except ValueError as exc:
        raise PlotDataError(f"Invalid numeric value: {value!r}") from exc

    if not math.isfinite(parsed):
        return float("nan")
    return parsed


def count_finite_pairs(x_values: list[float], y_values: list[float]) -> int:
    return sum(
        1
        for x_value, y_value in zip(x_values, y_values, strict=True)
        if math.isfinite(x_value) and math.isfinite(y_value)
    )


def validate_extracted_dataset(dataset: ExtractedDataset) -> ValidatedDataset:
    if dataset.confidence == "low":
        raise PlotDataError("Cannot use low-confidence extracted dataset")

    if dataset.data_start_line < 1 or dataset.data_end_line < dataset.data_start_line:
        raise PlotDataError("Dataset line range must be positive and increasing")

    if len(dataset.columns) < 2:
        raise PlotDataError("Dataset must contain at least two columns")

    expected_length = len(dataset.columns[0].values)
    if expected_length < 2:
        raise PlotDataError("Dataset must contain at least two rows")

    validated_columns: list[ValidatedColumn] = []
    used_names: dict[str, int] = {}

    for column in dataset.columns:
        base_name = column.name.strip()
        if not base_name:
            raise PlotDataError("Column names must not be empty")
        if len(column.values) != expected_length:
            raise PlotDataError("Every column must contain the same number of values")

        name = _unique_column_name(base_name, used_names)
        numeric_values = None
        if column.data_type == "number":
            numeric_values = [parse_numeric_value(value) for value in column.values]

        validated_columns.append(
            ValidatedColumn(
                name=name,
                unit=column.unit,
                data_type=column.data_type,
                values=list(column.values),
                numeric_values=numeric_values,
            )
        )

    return ValidatedDataset(
        source=dataset,
        columns=validated_columns,
        assumptions=list(dataset.assumptions),
    )


def build_dataset_metadata(dataset: ValidatedDataset) -> DatasetMetadata:
    columns = [
        DatasetColumnMetadata(
            name=column.name,
            unit=column.unit,
            data_type=column.data_type,
        )
        for column in dataset.columns
    ]

    return DatasetMetadata(columns=columns, assumptions=list(dataset.assumptions))


def _is_repeated_thousands_grouping(parts: list[str]) -> bool:
    if len(parts) < 3:
        return False
    if not 1 <= len(parts[0]) <= 3 or not parts[0].isdigit():
        return False
    return all(len(part) == 3 and part.isdigit() for part in parts[1:])


def _unique_column_name(base_name: str, used_names: dict[str, int]) -> str:
    count = used_names.get(base_name, 0) + 1
    used_names[base_name] = count
    if count == 1:
        return base_name
    return f"{base_name}_{count}"
