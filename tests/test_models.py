import pytest
from pydantic import ValidationError

from forelius.chapter import ChapterRole, ChapterSpec
from forelius.config import ChapterRef, ReportConfig
from forelius.elements import ElementKind, Plot, ReportElement, Table


def test_report_config_outline_default_is_not_shared() -> None:
    first = ReportConfig(
        discipline="geotechnical engineer",
        subject="pile foundation calculation",
        language="English",
        figure_label="Figure",
        table_label="Table",
    )
    second = ReportConfig(
        discipline="structural engineer",
        subject="retaining wall",
        language="English",
        figure_label="Figure",
        table_label="Table",
    )

    first.outline.append(ChapterRef(number=1, title="Introduction"))

    assert first.outline == [ChapterRef(number=1, title="Introduction")]
    assert second.outline == []


def test_chapter_spec_uses_flat_pointers_and_elements(tmp_path) -> None:
    image_path = tmp_path / "settlement.png"
    image_path.write_bytes(b"plot")
    plot = Plot(caption="Settlement profile", path=image_path)
    table = Table(caption="Loads", headers=["Case", "Load"], rows=[["A", "10 kN"]])

    spec = ChapterSpec(
        role=ChapterRole.BODY,
        title="Results",
        pointers=["Describe calculated settlements"],
        elements=[plot, table],
    )

    assert spec.pointers == ["Describe calculated settlements"]
    assert spec.elements == [plot, table]


def test_chapter_spec_with_feedback_appends_pointer_and_preserves_elements(tmp_path) -> None:
    image_path = tmp_path / "settlement.png"
    image_path.write_bytes(b"plot")
    plot = Plot(caption="Settlement profile", path=image_path)
    spec = ChapterSpec(
        role=ChapterRole.BODY,
        title="Results",
        pointers=["Describe calculated settlements"],
        elements=[plot],
    )

    revised = spec.with_feedback("Mention serviceability limit state")

    assert revised is not spec
    assert revised.pointers == [
        "Describe calculated settlements",
        "Mention serviceability limit state",
    ]
    assert revised.elements[0] is plot
    assert spec.pointers == ["Describe calculated settlements"]


def test_table_rejects_rows_with_different_length_than_headers() -> None:
    with pytest.raises(ValidationError, match="same length as headers"):
        Table(caption="Loads", headers=["Case", "Load"], rows=[["A"]])


def test_plot_rejects_missing_path(tmp_path) -> None:
    missing_path = tmp_path / "missing.png"

    with pytest.raises(ValidationError, match="Plot path must exist"):
        Plot(caption="Missing plot", path=missing_path)


def test_report_element_model_accepts_required_token_fields() -> None:
    element = ReportElement(
        element_id="fig_0001",
        kind=ElementKind.FIGURE,
        caption="Settlement profile",
        placement_token="<<FIG:fig_0001>>",
        reference_token="<<REF:fig_0001>>",
    )

    assert element.kind is ElementKind.FIGURE
    assert element.reference_token == "<<REF:fig_0001>>"
