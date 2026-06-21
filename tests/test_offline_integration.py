from unittest.mock import patch

from forelius.chapter import ChapterRole, ChapterSpec
from forelius.config import ReportConfig
from forelius.elements import Plot, Table
from forelius.generator import ChapterGenerator, GenerationOrder, generate_report
from forelius.render.markdown import MarkdownRenderer


def test_generate_report_introduction_last_renders_final_order_markdown(tmp_path) -> None:
    figure_path = tmp_path / "settlement.png"
    figure_path.write_bytes(b"plot")
    plot = Plot(caption="Settlement profile", path=figure_path)
    table = Table(
        caption="Load combinations",
        headers=["Case", "Load"],
        rows=[["A", "10 kN"]],
    )
    config = ReportConfig(
        discipline="geotechnical engineer",
        subject="pile foundation calculation",
        language="English",
        figure_label="Figure",
        table_label="Table",
    )
    specs = [
        ChapterSpec(
            role=ChapterRole.INTRODUCTION,
            title="Introduction",
            pointers=["Introduce the report scope."],
        ),
        ChapterSpec(
            role=ChapterRole.BODY,
            title="Results",
            pointers=["Discuss settlements and loads."],
            elements=[plot, table],
        ),
        ChapterSpec(
            role=ChapterRole.CONCLUSION,
            title="Conclusion",
            pointers=["State the final conclusion."],
        ),
    ]
    generation_sequence: list[str] = []

    def fake_dispatch(self, role, chapter_input):
        generation_sequence.append(chapter_input["chapter"]["title"])
        if role is ChapterRole.INTRODUCTION:
            return "# Introduction\nThis report describes the calculation scope."
        if role is ChapterRole.BODY:
            return (
                "# Results\n"
                "The settlement profile is shown in <<REF:fig_0001>>.\n"
                "<<FIG:fig_0001>>\n"
                "The governing loads are summarized in <<REF:tbl_0001>>.\n"
                "<<TBL:tbl_0001>>"
            )
        if role is ChapterRole.CONCLUSION:
            return "# Conclusion\nThe design satisfies the stated requirements."
        raise AssertionError(f"Unexpected role: {role}")

    with patch.object(ChapterGenerator, "_dispatch", fake_dispatch):
        sections = generate_report(config, specs, GenerationOrder.INTRODUCTION_LAST)

    markdown = MarkdownRenderer().render(config, sections)

    assert generation_sequence == ["Results", "Conclusion", "Introduction"]
    assert [section.chapter.title for section in sections] == [
        "Introduction",
        "Results",
        "Conclusion",
    ]
    assert markdown.index("# Introduction") < markdown.index("# Results")
    assert markdown.index("# Results") < markdown.index("# Conclusion")
    assert f"![Settlement profile]({figure_path})" in markdown
    assert "**Figure 1: Settlement profile**" in markdown
    assert "The settlement profile is shown in Figure 1." in markdown
    assert "**Table 1: Load combinations**" in markdown
    assert "| Case | Load |" in markdown
    assert "The governing loads are summarized in Table 1." in markdown
    assert "<<FIG:" not in markdown
    assert "<<TBL:" not in markdown
    assert "<<REF:" not in markdown
