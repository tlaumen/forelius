from unittest.mock import patch

from forelius.chapter import ChapterRole, ChapterSpec
from forelius.config import ChapterRef, ReportConfig
from forelius.elements import Plot, Table
from forelius.generator import (
    ChapterGenerator,
    GenerationOrder,
    chapter_generators,
    generate_report,
    order_sections,
)
from forelius.section import Section


def make_config() -> ReportConfig:
    return ReportConfig(
        discipline="geotechnical engineer",
        subject="pile foundation calculation",
        language="English",
        figure_label="Figure",
        table_label="Table",
    )


def make_plot(tmp_path, name="plot.png") -> Plot:
    image_path = tmp_path / name
    image_path.write_bytes(b"plot")
    return Plot(caption="Settlement profile", path=image_path)


def make_specs() -> list[ChapterSpec]:
    return [
        ChapterSpec(role=ChapterRole.INTRODUCTION, title="Introduction"),
        ChapterSpec(role=ChapterRole.BODY, title="Results"),
        ChapterSpec(role=ChapterRole.CONCLUSION, title="Conclusion"),
    ]


def test_chapter_generators_derives_outline_without_mutating_original_config() -> None:
    config = make_config()

    generators = list(chapter_generators(config, make_specs()))

    assert config.outline == []
    assert [generator.chapter for generator in generators] == [
        ChapterRef(number=1, title="Introduction"),
        ChapterRef(number=2, title="Results"),
        ChapterRef(number=3, title="Conclusion"),
    ]
    assert generators[0].config.outline == [
        ChapterRef(number=1, title="Introduction"),
        ChapterRef(number=2, title="Results"),
        ChapterRef(number=3, title="Conclusion"),
    ]


def test_chapter_generators_report_order_yields_report_order() -> None:
    generators = list(
        chapter_generators(make_config(), make_specs(), GenerationOrder.REPORT)
    )

    assert [generator.spec.title for generator in generators] == [
        "Introduction",
        "Results",
        "Conclusion",
    ]


def test_chapter_generators_introduction_last_yields_introductions_last() -> None:
    generators = list(
        chapter_generators(
            make_config(), make_specs(), GenerationOrder.INTRODUCTION_LAST
        )
    )

    assert [generator.spec.title for generator in generators] == [
        "Results",
        "Conclusion",
        "Introduction",
    ]
    assert [generator.chapter.number for generator in generators] == [2, 3, 1]


def test_order_sections_preserves_order_for_report_generation() -> None:
    first = Section(chapter=ChapterRef(number=2, title="Results"), text="# Results", line_element_map={})
    second = Section(chapter=ChapterRef(number=1, title="Introduction"), text="# Introduction", line_element_map={})

    ordered = order_sections([first, second], GenerationOrder.REPORT)

    assert ordered == [first, second]


def test_order_sections_sorts_for_introduction_last_generation() -> None:
    first = Section(chapter=ChapterRef(number=2, title="Results"), text="# Results", line_element_map={})
    second = Section(chapter=ChapterRef(number=1, title="Introduction"), text="# Introduction", line_element_map={})

    ordered = order_sections([first, second], GenerationOrder.INTRODUCTION_LAST)

    assert ordered == [second, first]


def test_generate_report_returns_final_report_order() -> None:
    specs = make_specs()

    def fake_dispatch(self, role, chapter_input):
        return f"# {chapter_input['chapter']['title']}"

    with patch.object(ChapterGenerator, "_dispatch", fake_dispatch):
        sections = generate_report(
            make_config(), specs, GenerationOrder.INTRODUCTION_LAST
        )

    assert [section.chapter.title for section in sections] == [
        "Introduction",
        "Results",
        "Conclusion",
    ]


def test_chapter_generator_builds_serializable_dispatch_input(tmp_path) -> None:
    plot = make_plot(tmp_path)
    table = Table(caption="Loads", headers=["Case", "Load"], rows=[["A", "10 kN"]])
    spec = ChapterSpec(
        role=ChapterRole.BODY,
        title="Results",
        pointers=["Discuss results"],
        elements=[plot, table],
    )
    generator = next(iter(chapter_generators(make_config(), [spec])))

    captured = {}

    def fake_dispatch(self, role, chapter_input):
        captured["role"] = role
        captured["input"] = chapter_input
        return "# Results\n<<FIG:fig_0001>>\n<<TBL:tbl_0001>>"

    with patch.object(ChapterGenerator, "_dispatch", fake_dispatch):
        section = generator.generate()

    assert section.chapter == ChapterRef(number=1, title="Results")
    assert captured["role"] is ChapterRole.BODY
    assert captured["input"]["chapter"] == {"number": 1, "title": "Results"}
    assert captured["input"]["pointers"] == ["Discuss results"]
    assert captured["input"]["elements"][0]["element_id"] == "fig_0001"
    assert captured["input"]["elements"][1]["element_id"] == "tbl_0001"


def test_chapter_draft_revise_regenerates_with_feedback_and_preserves_tokens(tmp_path) -> None:
    plot = make_plot(tmp_path)
    spec = ChapterSpec(
        role=ChapterRole.BODY,
        title="Results",
        pointers=["Discuss settlements"],
        elements=[plot],
    )
    generator = next(iter(chapter_generators(make_config(), [spec])))
    seen_inputs = []

    def fake_dispatch(self, role, chapter_input):
        seen_inputs.append(chapter_input)
        return "# Results\n<<FIG:fig_0001>>"

    with patch.object(ChapterGenerator, "_dispatch", fake_dispatch):
        draft = generator.draft()
        current = draft.current()
        revised = draft.revise("Mention serviceability")
        accepted = draft.accept()

    assert current.chapter == ChapterRef(number=1, title="Results")
    assert revised is accepted
    assert seen_inputs[0]["pointers"] == ["Discuss settlements"]
    assert seen_inputs[1]["pointers"] == [
        "Discuss settlements",
        "Mention serviceability",
    ]
    assert seen_inputs[0]["elements"][0]["element_id"] == "fig_0001"
    assert seen_inputs[1]["elements"][0]["element_id"] == "fig_0001"


def test_dispatch_routes_introduction_to_generated_baml_client(monkeypatch) -> None:
    from baml_client import types as baml_types
    from baml_client.sync_client import b

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    generator = next(iter(chapter_generators(make_config(), [make_specs()[0]])))
    chapter_input = {
        "config": generator.config.model_dump(mode="json"),
        "chapter": generator.chapter.model_dump(mode="json"),
        "pointers": [],
        "elements": [],
    }

    with patch.object(b, "ReportIntroduction", return_value="# Introduction") as call:
        result = generator._dispatch(ChapterRole.INTRODUCTION, chapter_input)

    assert result == "# Introduction"
    call.assert_called_once()
    assert isinstance(call.call_args.args[0], baml_types.ChapterInput)


def test_dispatch_routes_body_to_generated_baml_client(monkeypatch) -> None:
    from baml_client.sync_client import b

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    generator = next(iter(chapter_generators(make_config(), [make_specs()[1]])))
    chapter_input = {
        "config": generator.config.model_dump(mode="json"),
        "chapter": generator.chapter.model_dump(mode="json"),
        "pointers": ["Discuss results"],
        "elements": [],
    }

    with patch.object(b, "ReportChapter", return_value="# Results") as call:
        result = generator._dispatch(ChapterRole.BODY, chapter_input)

    assert result == "# Results"
    call.assert_called_once()
    assert call.call_args.args[0].pointers == ["Discuss results"]


def test_dispatch_routes_conclusion_to_generated_baml_client(monkeypatch) -> None:
    from baml_client.sync_client import b

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    generator = next(iter(chapter_generators(make_config(), [make_specs()[2]])))
    chapter_input = {
        "config": generator.config.model_dump(mode="json"),
        "chapter": generator.chapter.model_dump(mode="json"),
        "pointers": [],
        "elements": [],
    }

    with patch.object(b, "ReportConclusion", return_value="# Conclusion") as call:
        result = generator._dispatch(ChapterRole.CONCLUSION, chapter_input)

    assert result == "# Conclusion"
    call.assert_called_once()
    assert call.call_args.args[0].chapter.title == "Conclusion"
