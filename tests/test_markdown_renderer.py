import pytest

from forelius.config import ChapterRef, ReportConfig
from forelius.elements import ElementRegistry, Plot, Table
from forelius.render.markdown import MarkdownRenderer, MarkdownRenderError
from forelius.section import Section, parse_section


def make_config() -> ReportConfig:
    return ReportConfig(
        discipline="geotechnical engineer",
        subject="pile foundation calculation",
        language="English",
        figure_label="Figure",
        table_label="Table",
    )


def make_plot(tmp_path, name="plot.png", caption="Settlement profile") -> Plot:
    image_path = tmp_path / name
    image_path.write_bytes(b"plot")
    return Plot(caption=caption, path=image_path)


def test_markdown_renderer_renders_figure_and_inline_reference(tmp_path) -> None:
    plot = make_plot(tmp_path)
    resolved = ElementRegistry().resolve([plot])
    section = parse_section(
        ChapterRef(number=1, title="Results"),
        "# Results\nSee <<REF:fig_0001>>.\n<<FIG:fig_0001>>",
        resolved,
    )

    markdown = MarkdownRenderer().render(make_config(), [section])

    assert "See Figure 1." in markdown
    assert f"![Settlement profile]({plot.path})" in markdown
    assert "**Figure 1: Settlement profile**" in markdown


def test_markdown_renderer_renders_table_and_escapes_pipes() -> None:
    table = Table(
        caption="Loads",
        headers=["Case", "Description"],
        rows=[["A", "service | limit"]],
    )
    resolved = ElementRegistry().resolve([table])
    section = parse_section(
        ChapterRef(number=1, title="Results"),
        "# Results\n<<TBL:tbl_0001>>",
        resolved,
    )

    markdown = MarkdownRenderer().render(make_config(), [section])

    assert "**Table 1: Loads**" in markdown
    assert "| Case | Description |" in markdown
    assert "| --- | --- |" in markdown
    assert r"| A | service \| limit |" in markdown


def test_markdown_renderer_numbers_from_final_section_order(tmp_path) -> None:
    late_plot = make_plot(tmp_path, "late.png", "Late generated")
    early_plot = make_plot(tmp_path, "early.png", "Early rendered")
    registry = ElementRegistry()
    late_resolved, early_resolved = registry.resolve([late_plot, early_plot])
    late_section = parse_section(
        ChapterRef(number=2, title="Late"),
        "# Late\nSee <<REF:fig_0001>>.\n<<FIG:fig_0001>>",
        [late_resolved],
    )
    early_section = parse_section(
        ChapterRef(number=1, title="Early"),
        "# Early\nSee <<REF:fig_0002>>.\n<<FIG:fig_0002>>",
        [early_resolved],
    )

    markdown = MarkdownRenderer().render(make_config(), [early_section, late_section])

    assert "See Figure 1.\n![Early rendered]" in markdown
    assert "**Figure 1: Early rendered**" in markdown
    assert "See Figure 2.\n![Late generated]" in markdown
    assert "**Figure 2: Late generated**" in markdown


def test_markdown_renderer_raises_for_unknown_reference_token(tmp_path) -> None:
    plot = make_plot(tmp_path)
    resolved = ElementRegistry().resolve([plot])
    section = Section(
        chapter=ChapterRef(number=1, title="Results"),
        text="# Results\nSee <<REF:fig_9999>>.\n<<FIG:fig_0001>>",
        line_element_map={2: resolved[0]},
    )

    with pytest.raises(MarkdownRenderError, match="Unknown reference token"):
        MarkdownRenderer().render(make_config(), [section])
