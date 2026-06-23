from pathlib import Path
from unittest.mock import patch

import pytest
from baml_client import types as baml_types
from baml_client.sync_client import b

from forelius.elements import Plot
from forelius.plotting import PlotDataError, PlotGenerationSession, PlotIntentError
from forelius.plotting import service
from forelius.plotting.service import generate_plot_from_freeform, generate_plot_session


def baml_dataset(
    confidence: baml_types.ExtractionConfidence = baml_types.ExtractionConfidence.HIGH,
) -> baml_types.ExtractedDataset:
    return baml_types.ExtractedDataset(
        data_start_line=2,
        data_end_line=4,
        confidence=confidence,
        assumptions=["Column names inferred from header."],
        columns=[
            baml_types.ExtractedColumn(
                name="X",
                unit="m",
                data_type=baml_types.ExtractedDataType.NUMBER,
                values=["0", "1", "2"],
            ),
            baml_types.ExtractedColumn(
                name="Y",
                unit="mm",
                data_type=baml_types.ExtractedDataType.NUMBER,
                values=["0", "10", "20"],
            ),
        ],
    )


def baml_intent(**overrides) -> baml_types.XYPlotIntent:
    options = overrides.pop(
        "options",
        baml_types.XYPlotOptions(
            title="Y against X",
            x_label="X (m)",
            y_label="Y (mm)",
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
        "x": "X",
        "y": "Y",
        "caption": "Y against X.",
        "options": options,
    }
    values.update(overrides)
    return baml_types.XYPlotIntent(**values)


@pytest.fixture(autouse=True)
def no_live_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "ensure_initialized", lambda: None)


def test_generate_plot_session_calls_baml_validation_intent_and_rendering(tmp_path: Path) -> None:
    extracted = baml_dataset()
    intent = baml_intent()

    with (
        patch.object(b, "ExtractDatasetFromFreeform", return_value=extracted) as extract,
        patch.object(b, "CreateXYPlotIntent", return_value=intent) as create,
    ):
        session = generate_plot_session(
            "Maak een grafiek.\nX,Y\n0,0\n1,10\n2,20",
            tmp_path,
            "initial",
        )

    assert isinstance(session, PlotGenerationSession)
    assert isinstance(session.plot, Plot)
    assert session.plot.path.name == "initial.png"
    assert session.plot.path.exists()
    assert session.dataset.assumptions == ["Column names inferred from header."]
    assert session.intent is intent
    extract.assert_called_once()
    assert extract.call_args.args[0].startswith("1: Maak een grafiek.")
    create.assert_called_once()
    create_input = create.call_args.args[0]
    assert isinstance(create_input, baml_types.CreateXYPlotIntentInput)
    assert create_input.request.startswith("Maak een grafiek")
    assert create_input.dataset.columns[0].model_dump() == {
        "name": "X",
        "unit": "m",
        "data_type": baml_types.ExtractedDataType.NUMBER,
    }
    assert "values" not in create_input.dataset.columns[0].model_dump()


def test_generate_plot_from_freeform_returns_plot(tmp_path: Path) -> None:
    with (
        patch.object(b, "ExtractDatasetFromFreeform", return_value=baml_dataset()),
        patch.object(b, "CreateXYPlotIntent", return_value=baml_intent()),
    ):
        plot = generate_plot_from_freeform("plot x y", tmp_path, "plot")

    assert isinstance(plot, Plot)
    assert plot.path.name == "plot.png"


def test_low_confidence_extraction_prevents_intent_creation(tmp_path: Path) -> None:
    with (
        patch.object(
            b,
            "ExtractDatasetFromFreeform",
            return_value=baml_dataset(baml_types.ExtractionConfidence.LOW),
        ),
        patch.object(b, "CreateXYPlotIntent", return_value=baml_intent()) as create,
    ):
        with pytest.raises(PlotDataError, match="low-confidence"):
            generate_plot_session("plot x y", tmp_path, "bad")

    create.assert_not_called()
    assert not list(tmp_path.glob("*.png"))


def test_invalid_intent_prevents_rendering(tmp_path: Path) -> None:
    with (
        patch.object(b, "ExtractDatasetFromFreeform", return_value=baml_dataset()),
        patch.object(b, "CreateXYPlotIntent", return_value=baml_intent(y="Missing")),
    ):
        with pytest.raises(PlotIntentError, match="does not exist"):
            generate_plot_session("plot x y", tmp_path, "bad")

    assert not list(tmp_path.glob("*.png"))


def test_revision_reuses_dataset_calls_revision_baml_and_overwrites_plot(tmp_path: Path) -> None:
    initial_intent = baml_intent()
    revised_intent = baml_intent(
        options=initial_intent.options.model_copy(
            update={
                "line_style": baml_types.PlotLineStyle.NONE,
                "marker": baml_types.PlotMarker.CIRCLE,
            }
        )
    )

    with (
        patch.object(b, "ExtractDatasetFromFreeform", return_value=baml_dataset()),
        patch.object(b, "CreateXYPlotIntent", return_value=initial_intent),
    ):
        session = generate_plot_session("plot x y", tmp_path, "plot")

    original_path = session.plot.path
    original_mtime = original_path.stat().st_mtime_ns

    with patch.object(b, "ReviseXYPlotIntent", return_value=revised_intent) as revise:
        revised = session.revise("Maak er alleen punten van.")

    assert revised.dataset is session.dataset
    assert revised.intent is revised_intent
    assert revised.plot.path == original_path
    assert revised.plot.path.exists()
    assert revised.plot.path.stat().st_mtime_ns >= original_mtime
    revise.assert_called_once()
    revise_input = revise.call_args.args[0]
    assert isinstance(revise_input, baml_types.ReviseXYPlotIntentInput)
    assert revise_input.current_intent is initial_intent
    assert revise_input.feedback == "Maak er alleen punten van."
    assert revise_input.dataset.columns[0].name == "X"
    assert not (tmp_path / "plot_2.png").exists()
