import math

import pytest

from forelius.plotting import (
    ExtractedColumn,
    ExtractedDataset,
    PlotDataError,
    build_dataset_metadata,
    count_finite_pairs,
    number_input_lines,
    parse_numeric_value,
    validate_extracted_dataset,
)


def make_dataset(**overrides) -> ExtractedDataset:
    values = {
        "data_start_line": 2,
        "data_end_line": 4,
        "confidence": "high",
        "assumptions": ["Header inferred from first table row."],
        "columns": [
            ExtractedColumn(
                name="Depth",
                unit="m",
                data_type="number",
                values=["0", "1,5", "2.0"],
            ),
            ExtractedColumn(
                name="Settlement",
                unit="mm",
                data_type="number",
                values=["0", "12.5", "-"],
            ),
        ],
    }
    values.update(overrides)
    return ExtractedDataset(**values)


def test_number_input_lines_prefixes_each_line() -> None:
    assert number_input_lines("header\n1, 2\n3, 4") == "1: header\n2: 1, 2\n3: 3, 4"


def test_validate_extracted_dataset_parses_numeric_columns_and_preserves_source() -> None:
    dataset = make_dataset()

    validated = validate_extracted_dataset(dataset)

    assert validated.source is dataset
    assert validated.assumptions == ["Header inferred from first table row."]
    assert validated.columns[0].name == "Depth"
    assert validated.columns[0].numeric_values == [0.0, 1.5, 2.0]
    assert validated.columns[1].numeric_values is not None
    assert validated.columns[1].numeric_values[:2] == [0.0, 12.5]
    assert math.isnan(validated.columns[1].numeric_values[2])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.1", 4.1),
        ("4,1", 4.1),
        ("1,234.56", 1234.56),
        ("1.234,56", 1234.56),
        ("1000", 1000.0),
        ("-12,5", -12.5),
        ("+12.5", 12.5),
        ("1.234.567", 1234567.0),
        ("1,234,567", 1234567.0),
    ],
)
def test_parse_numeric_value_supports_expected_number_formats(raw: str, expected: float) -> None:
    assert parse_numeric_value(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "-", "—", "n/a", "NA", "null", "none", "geen", "NaN", "Infinity", "-inf"],
)
def test_parse_numeric_value_normalizes_missing_and_nonfinite_tokens_to_nan(raw: str) -> None:
    assert math.isnan(parse_numeric_value(raw))


@pytest.mark.parametrize("raw", ["10 kN", "12%", "1..2", "1,", "abc"])
def test_parse_numeric_value_rejects_non_numeric_values(raw: str) -> None:
    with pytest.raises(PlotDataError):
        parse_numeric_value(raw)


def test_validate_extracted_dataset_rejects_low_confidence() -> None:
    with pytest.raises(PlotDataError, match="low-confidence"):
        validate_extracted_dataset(make_dataset(confidence="low"))


@pytest.mark.parametrize(
    "dataset",
    [
        make_dataset(data_start_line=0),
        make_dataset(data_start_line=5, data_end_line=4),
    ],
)
def test_validate_extracted_dataset_rejects_invalid_line_ranges(dataset: ExtractedDataset) -> None:
    with pytest.raises(PlotDataError, match="line range"):
        validate_extracted_dataset(dataset)


def test_validate_extracted_dataset_rejects_fewer_than_two_columns() -> None:
    dataset = make_dataset(columns=[make_dataset().columns[0]])

    with pytest.raises(PlotDataError, match="at least two columns"):
        validate_extracted_dataset(dataset)


def test_validate_extracted_dataset_rejects_empty_column_names() -> None:
    dataset = make_dataset(
        columns=[
            ExtractedColumn(name=" ", data_type="number", values=["1", "2"]),
            ExtractedColumn(name="Y", data_type="number", values=["3", "4"]),
        ]
    )

    with pytest.raises(PlotDataError, match="Column names"):
        validate_extracted_dataset(dataset)


def test_validate_extracted_dataset_normalizes_duplicate_column_names() -> None:
    dataset = make_dataset(
        columns=[
            ExtractedColumn(name="Value", data_type="number", values=["1", "2"]),
            ExtractedColumn(name="Value", data_type="number", values=["3", "4"]),
            ExtractedColumn(name="Value", data_type="number", values=["5", "6"]),
        ]
    )

    validated = validate_extracted_dataset(dataset)

    assert [column.name for column in validated.columns] == ["Value", "Value_2", "Value_3"]


def test_validate_extracted_dataset_rejects_unequal_column_lengths() -> None:
    dataset = make_dataset(
        columns=[
            ExtractedColumn(name="X", data_type="number", values=["1", "2"]),
            ExtractedColumn(name="Y", data_type="number", values=["3"]),
        ]
    )

    with pytest.raises(PlotDataError, match="same number"):
        validate_extracted_dataset(dataset)


def test_validate_extracted_dataset_rejects_fewer_than_two_rows() -> None:
    dataset = make_dataset(
        columns=[
            ExtractedColumn(name="X", data_type="number", values=["1"]),
            ExtractedColumn(name="Y", data_type="number", values=["3"]),
        ]
    )

    with pytest.raises(PlotDataError, match="at least two rows"):
        validate_extracted_dataset(dataset)


def test_count_finite_pairs_counts_only_pairs_with_two_finite_values() -> None:
    assert count_finite_pairs([1.0, math.nan, 3.0, 4.0], [1.0, 2.0, math.nan, 4.0]) == 2


def test_build_dataset_metadata_uses_only_column_selection_fields() -> None:
    validated = validate_extracted_dataset(make_dataset())

    metadata = build_dataset_metadata(validated)

    assert metadata.assumptions == ["Header inferred from first table row."]
    assert metadata.columns[0].model_dump() == {
        "name": "Depth",
        "unit": "m",
        "data_type": "number",
    }
    assert metadata.columns[1].model_dump() == {
        "name": "Settlement",
        "unit": "mm",
        "data_type": "number",
    }
    assert "numeric_values" not in metadata.model_dump(mode="json")["columns"][0]


def test_build_dataset_metadata_includes_non_numeric_columns_without_values() -> None:
    dataset = make_dataset(
        columns=[
            ExtractedColumn(name="Load case", data_type="category", values=["A", "B"]),
            ExtractedColumn(name="Force", unit="kN", data_type="number", values=["10", "20"]),
        ]
    )
    validated = validate_extracted_dataset(dataset)

    metadata = build_dataset_metadata(validated)

    assert metadata.columns[0].model_dump() == {
        "name": "Load case",
        "unit": None,
        "data_type": "category",
    }
