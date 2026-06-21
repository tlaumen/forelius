import pytest

from forelius.config import ChapterRef
from forelius.elements import ElementRegistry, Plot, Table
from forelius.section import SectionParseError, parse_section


def make_plot(tmp_path, name="plot.png") -> Plot:
    image_path = tmp_path / name
    image_path.write_bytes(b"plot")
    return Plot(caption="Settlement profile", path=image_path)


def test_parse_section_maps_placement_lines_with_zero_based_indexes(tmp_path) -> None:
    plot = make_plot(tmp_path)
    table = Table(caption="Loads", headers=["Case", "Load"], rows=[["A", "10 kN"]])
    elements = ElementRegistry().resolve([plot, table])
    text = "\n".join(
        [
            "# Results",
            "See <<REF:fig_0001>> and <<REF:tbl_0001>>.",
            "<<FIG:fig_0001>>",
            "The governing load case is shown below.",
            "<<TBL:tbl_0001>>",
        ]
    )

    section = parse_section(ChapterRef(number=2, title="Results"), text, elements)

    assert section.text == text
    assert section.line_element_map[2] is elements[0]
    assert section.line_element_map[4] is elements[1]


def test_parse_section_rejects_missing_expected_placement_token(tmp_path) -> None:
    plot = make_plot(tmp_path)
    elements = ElementRegistry().resolve([plot])
    text = "# Results\nThe figure is discussed but not placed."

    with pytest.raises(SectionParseError, match="Missing placement token"):
        parse_section(ChapterRef(number=2, title="Results"), text, elements)


def test_parse_section_rejects_duplicate_placement_token(tmp_path) -> None:
    plot = make_plot(tmp_path)
    elements = ElementRegistry().resolve([plot])
    text = "\n".join(
        [
            "# Results",
            "<<FIG:fig_0001>>",
            "Repeated below.",
            "<<FIG:fig_0001>>",
        ]
    )

    with pytest.raises(SectionParseError, match="Duplicate placement token"):
        parse_section(ChapterRef(number=2, title="Results"), text, elements)


def test_parse_section_rejects_unknown_placement_token(tmp_path) -> None:
    plot = make_plot(tmp_path)
    elements = ElementRegistry().resolve([plot])
    text = "# Results\n<<FIG:fig_0002>>\n<<FIG:fig_0001>>"

    with pytest.raises(SectionParseError, match="Unknown placement token"):
        parse_section(ChapterRef(number=2, title="Results"), text, elements)


def test_parse_section_rejects_unknown_inline_reference_token(tmp_path) -> None:
    plot = make_plot(tmp_path)
    elements = ElementRegistry().resolve([plot])
    text = "# Results\nSee <<REF:fig_0002>>.\n<<FIG:fig_0001>>"

    with pytest.raises(SectionParseError, match="Unknown reference token"):
        parse_section(ChapterRef(number=2, title="Results"), text, elements)


def test_parse_section_rejects_embedded_placement_token(tmp_path) -> None:
    plot = make_plot(tmp_path)
    elements = ElementRegistry().resolve([plot])
    text = "# Results\nPlace it here: <<FIG:fig_0001>>"

    with pytest.raises(SectionParseError, match="own line"):
        parse_section(ChapterRef(number=2, title="Results"), text, elements)
