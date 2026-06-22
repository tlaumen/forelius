import pytest

from forelius.chapter import ChapterRole, ChapterSpec
from forelius.config import ChapterRef, ReportConfig
from forelius.elements import Plot, Table
from forelius.generator import GenerationOrder
from forelius.interactive import (
    InteractiveReportAborted,
    _CHAPTER_ROLE_CHOICES,
    _ELEMENT_CHOICES,
    _REVIEW_ACTION_CHOICES,
    _parse_csv_table,
    _print_message,
    _prompt_chapter_elements,
    _prompt_chapter_pointers,
    _prompt_chapter_spec,
    _prompt_chapter_specs,
    _prompt_choice,
    _prompt_figure,
    _prompt_report_config,
    _prompt_report_inputs,
    _prompt_table,
    _prompt_required_text,
    _prompt_yes_no,
    _review_chapter_drafts,
    prompt_for_report,
)
from forelius.section import Section


def make_config() -> ReportConfig:
    return ReportConfig(
        discipline="geotechnisch ingenieur",
        subject="paalfundering",
        language="Nederlands",
        figure_label="Figuur",
        table_label="Tabel",
    )


def test_interactive_module_exports_abort_exception() -> None:
    assert issubclass(InteractiveReportAborted, Exception)


def test_review_action_choices_are_dutch_and_ordered() -> None:
    assert list(_REVIEW_ACTION_CHOICES) == ["accepteren", "herzien", "afbreken"]
    assert _REVIEW_ACTION_CHOICES == {
        "accepteren": "accept",
        "herzien": "revise",
        "afbreken": "abort",
    }


def test_print_message_uses_prompt_toolkit_print(monkeypatch) -> None:
    printed_messages: list[str] = []
    monkeypatch.setattr(
        "forelius.interactive.print_formatted_text",
        lambda message: printed_messages.append(message),
    )

    _print_message("Hello")

    assert printed_messages == ["Hello"]


def test_prompt_required_text_reprompts_until_non_empty(monkeypatch) -> None:
    responses = iter(["  ", " Report title "])
    printed_messages: list[str] = []
    monkeypatch.setattr("forelius.interactive.prompt", lambda message: next(responses))
    monkeypatch.setattr(
        "forelius.interactive.print_formatted_text",
        lambda message: printed_messages.append(message),
    )

    value = _prompt_required_text("Title")

    assert value == "Report title"
    assert printed_messages == ["Title is required"]


def test_prompt_required_text_returns_default_for_empty_input(monkeypatch) -> None:
    prompt_messages: list[str] = []
    monkeypatch.setattr(
        "forelius.interactive.prompt",
        lambda message: prompt_messages.append(message) or "",
    )

    value = _prompt_required_text("Figuurlabel", default="Figuur")

    assert value == "Figuur"
    assert prompt_messages == ["Figuurlabel [Figuur]: "]


def test_prompt_choice_uses_prompt_toolkit_choice(monkeypatch) -> None:
    captured_call: dict[str, object] = {}

    def fake_choice(**kwargs):
        captured_call.update(kwargs)
        return "body"

    monkeypatch.setattr("forelius.interactive.choice", fake_choice)

    value = _prompt_choice("Role", ["introduction", "body", "conclusion"])

    assert value == "body"
    assert captured_call == {
        "message": "Role:",
        "options": [
            ("introduction", "introduction"),
            ("body", "body"),
            ("conclusion", "conclusion"),
        ],
    }


def test_prompt_choice_rejects_empty_choices() -> None:
    with pytest.raises(ValueError, match="choices must not be empty"):
        _prompt_choice("Role", [])


def test_prompt_yes_no_returns_default_for_empty_input(monkeypatch) -> None:
    monkeypatch.setattr("forelius.interactive.prompt", lambda message: "")

    assert _prompt_yes_no("Add chapter?", default=True) is True


def test_prompt_yes_no_accepts_yes_and_no(monkeypatch) -> None:
    responses = iter(["yes", "n"])
    monkeypatch.setattr("forelius.interactive.prompt", lambda message: next(responses))

    assert _prompt_yes_no("Add chapter?") is True
    assert _prompt_yes_no("Add chapter?", default=True) is False


def test_prompt_yes_no_reprompts_after_invalid_input(monkeypatch) -> None:
    responses = iter(["maybe", "y"])
    printed_messages: list[str] = []
    monkeypatch.setattr("forelius.interactive.prompt", lambda message: next(responses))
    monkeypatch.setattr(
        "forelius.interactive.print_formatted_text",
        lambda message: printed_messages.append(message),
    )

    assert _prompt_yes_no("Add chapter?") is True
    assert printed_messages == ["Enter yes or no"]


def test_element_choices_are_dutch_and_ordered() -> None:
    assert list(_ELEMENT_CHOICES) == ["figuur", "tabel", "klaar"]
    assert _ELEMENT_CHOICES == {
        "figuur": "figure",
        "tabel": "table",
        "klaar": "done",
    }


def test_chapter_role_choices_are_dutch_and_ordered() -> None:
    assert list(_CHAPTER_ROLE_CHOICES) == [
        "inleiding",
        "conclusie",
        "ander hoofdstuk",
    ]
    assert _CHAPTER_ROLE_CHOICES["inleiding"] is ChapterRole.INTRODUCTION
    assert _CHAPTER_ROLE_CHOICES["conclusie"] is ChapterRole.CONCLUSION
    assert _CHAPTER_ROLE_CHOICES["ander hoofdstuk"] is ChapterRole.BODY


def test_prompt_chapter_spec_builds_chapter_with_dutch_prompts(monkeypatch) -> None:
    required_text_labels: list[str] = []
    choice_calls: list[tuple[str, list[str]]] = []
    yes_no_calls: list[tuple[str, bool]] = []
    required_text_values = iter([
        "Inleiding",
        "Beschrijf het doel van het rapport.",
        "Noem de uitgangspunten.",
    ])
    yes_no_values = iter([True, True, False])

    def fake_prompt_required_text(label: str) -> str:
        required_text_labels.append(label)
        return next(required_text_values)

    def fake_prompt_choice(label: str, choices: list[str]) -> str:
        choice_calls.append((label, choices))
        return "inleiding"

    def fake_prompt_yes_no(label: str, default: bool = False) -> bool:
        yes_no_calls.append((label, default))
        return next(yes_no_values)

    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        fake_prompt_required_text,
    )
    monkeypatch.setattr("forelius.interactive._prompt_choice", fake_prompt_choice)
    monkeypatch.setattr("forelius.interactive._prompt_yes_no", fake_prompt_yes_no)

    spec = _prompt_chapter_spec()

    assert required_text_labels == ["Hoofdstuktitel", "Pointer", "Pointer"]
    assert choice_calls == [
        ("Soort hoofdstuk", ["inleiding", "conclusie", "ander hoofdstuk"])
    ]
    assert yes_no_calls == [
        ("Pointer toevoegen?", True),
        ("Pointer toevoegen?", True),
        ("Pointer toevoegen?", True),
    ]
    assert spec.title == "Inleiding"
    assert spec.role is ChapterRole.INTRODUCTION
    assert spec.pointers == [
        "Beschrijf het doel van het rapport.",
        "Noem de uitgangspunten.",
    ]
    assert spec.elements == []


def test_prompt_chapter_spec_allows_no_pointers(monkeypatch) -> None:
    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        lambda label: "Resultaten",
    )
    monkeypatch.setattr(
        "forelius.interactive._prompt_choice",
        lambda label, choices: "ander hoofdstuk",
    )
    monkeypatch.setattr(
        "forelius.interactive._prompt_yes_no",
        lambda label, default=False: False,
    )

    spec = _prompt_chapter_spec()

    assert spec.title == "Resultaten"
    assert spec.role is ChapterRole.BODY
    assert spec.pointers == []
    assert spec.elements == []


def test_prompt_chapter_specs_adds_fixed_intro_and_conclusion(monkeypatch) -> None:
    required_text_labels: list[str] = []
    yes_no_calls: list[tuple[str, bool]] = []
    body_titles = iter(["Resultaten", "Beschouwing"])
    add_more_values = iter([True, False])

    def fake_prompt_required_text(label: str) -> str:
        required_text_labels.append(label)
        return next(body_titles)

    def fake_prompt_yes_no(label: str, default: bool = False) -> bool:
        yes_no_calls.append((label, default))
        return next(add_more_values)

    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        fake_prompt_required_text,
    )
    monkeypatch.setattr("forelius.interactive._prompt_yes_no", fake_prompt_yes_no)

    specs = _prompt_chapter_specs()

    assert required_text_labels == ["Hoofdstuktitel", "Hoofdstuktitel"]
    assert yes_no_calls == [
        ("Nog een hoofdstuk toevoegen?", True),
        ("Nog een hoofdstuk toevoegen?", True),
    ]
    assert [spec.title for spec in specs] == [
        "Inleiding",
        "Resultaten",
        "Beschouwing",
        "Conclusie",
    ]
    assert [spec.role for spec in specs] == [
        ChapterRole.INTRODUCTION,
        ChapterRole.BODY,
        ChapterRole.BODY,
        ChapterRole.CONCLUSION,
    ]
    assert all(spec.pointers == [] for spec in specs)
    assert all(spec.elements == [] for spec in specs)


def test_prompt_chapter_specs_requires_at_least_one_body_chapter(monkeypatch) -> None:
    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        lambda label: "Resultaten",
    )
    monkeypatch.setattr(
        "forelius.interactive._prompt_yes_no",
        lambda label, default=False: False,
    )

    specs = _prompt_chapter_specs()

    assert [spec.title for spec in specs] == ["Inleiding", "Resultaten", "Conclusie"]
    assert [spec.role for spec in specs] == [
        ChapterRole.INTRODUCTION,
        ChapterRole.BODY,
        ChapterRole.CONCLUSION,
    ]


def test_prompt_chapter_pointers_assigns_pointers_per_chapter(monkeypatch) -> None:
    specs = [
        ChapterSpec(role=ChapterRole.INTRODUCTION, title="Inleiding"),
        ChapterSpec(role=ChapterRole.BODY, title="Resultaten"),
    ]
    printed_messages: list[str] = []
    yes_no_values = iter([True, False, True, True, False])
    pointer_values = iter([
        "Beschrijf het doel.",
        "Bespreek de resultaten.",
        "Noem de maatgevende waarde.",
    ])

    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )
    monkeypatch.setattr(
        "forelius.interactive._prompt_yes_no",
        lambda label, default=False: next(yes_no_values),
    )
    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        lambda label: next(pointer_values),
    )

    updated_specs = _prompt_chapter_pointers(specs)

    assert printed_messages == [
        "Pointers zijn inhoudelijke aanwijzingen voor de generator.\n"
        "Voorbeeld: \"Leg het doel en de scope van het rapport uit.\"",
        "Pointers zijn inhoudelijke aanwijzingen voor de generator.\n"
        "Voorbeeld: \"Leg het doel en de scope van het rapport uit.\"",
    ]
    assert updated_specs[0].pointers == ["Beschrijf het doel."]
    assert updated_specs[1].pointers == [
        "Bespreek de resultaten.",
        "Noem de maatgevende waarde.",
    ]
    assert specs[0].pointers == []
    assert specs[1].pointers == []


def test_prompt_chapter_pointers_allows_zero_pointers_and_replaces_existing(monkeypatch) -> None:
    specs = [
        ChapterSpec(
            role=ChapterRole.CONCLUSION,
            title="Conclusie",
            pointers=["Existing pointer"],
        )
    ]

    monkeypatch.setattr("forelius.interactive._print_message", lambda message: None)
    monkeypatch.setattr(
        "forelius.interactive._prompt_yes_no",
        lambda label, default=False: False,
    )

    updated_specs = _prompt_chapter_pointers(specs)

    assert updated_specs[0].pointers == []
    assert specs[0].pointers == ["Existing pointer"]


def test_prompt_figure_warns_for_missing_path_and_disables_strict_validation(
    monkeypatch, tmp_path
) -> None:
    labels: list[str] = []
    printed_messages: list[str] = []
    missing_path = tmp_path / "missing.png"
    values = iter(["Zakking", str(missing_path)])

    def fake_prompt_required_text(label: str) -> str:
        labels.append(label)
        return next(values)

    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        fake_prompt_required_text,
    )
    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )

    plot = _prompt_figure()

    assert labels == ["Figuurbijschrift", "Figuurpad"]
    assert plot.caption == "Zakking"
    assert plot.path == missing_path
    assert plot.validate_path_exists is False
    assert printed_messages == [f"Waarschuwing: figuurpad bestaat niet: {missing_path}"]


def test_prompt_figure_does_not_warn_for_existing_path(monkeypatch, tmp_path) -> None:
    existing_path = tmp_path / "plot.png"
    existing_path.write_bytes(b"plot")
    printed_messages: list[str] = []
    values = iter(["Zakking", str(existing_path)])

    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        lambda label: next(values),
    )
    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )

    plot = _prompt_figure()

    assert plot.path == existing_path
    assert printed_messages == []


def test_prompt_table_reprompts_after_invalid_csv(monkeypatch) -> None:
    labels: list[str] = []
    printed_messages: list[str] = []
    prompt_calls: list[tuple[str, bool]] = []
    csv_values = iter(["Case,Load", "Case,Load\nA,10 kN"])

    def fake_prompt(message: str, multiline: bool = False) -> str:
        prompt_calls.append((message, multiline))
        return next(csv_values)

    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        lambda label: labels.append(label) or "Belastingen",
    )
    monkeypatch.setattr("forelius.interactive.prompt", fake_prompt)
    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )

    table = _prompt_table()

    assert labels == ["Tabelbijschrift"]
    assert prompt_calls == [("Plak CSV-tabel: ", True), ("Plak CSV-tabel: ", True)]
    assert printed_messages == ["CSV input must include at least one data row"]
    assert table == Table(
        caption="Belastingen",
        headers=["Case", "Load"],
        rows=[["A", "10 kN"]],
    )


def test_prompt_chapter_elements_attaches_figures_and_tables(monkeypatch) -> None:
    specs = [
        ChapterSpec(role=ChapterRole.BODY, title="Resultaten"),
        ChapterSpec(
            role=ChapterRole.CONCLUSION,
            title="Conclusie",
            elements=[Table(caption="Old", headers=["A"], rows=[["B"]])],
        ),
    ]
    plot = Plot(caption="Zakking", path="missing.png", validate_path_exists=False)
    table = Table(caption="Belastingen", headers=["Case"], rows=[["A"]])
    printed_messages: list[str] = []
    choice_calls: list[tuple[str, list[str]]] = []
    choices = iter(["figuur", "tabel", "klaar", "klaar"])

    def fake_prompt_choice(label: str, choices_: list[str]) -> str:
        choice_calls.append((label, choices_))
        return next(choices)

    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )
    monkeypatch.setattr("forelius.interactive._prompt_choice", fake_prompt_choice)
    monkeypatch.setattr("forelius.interactive._prompt_figure", lambda: plot)
    monkeypatch.setattr("forelius.interactive._prompt_table", lambda: table)

    updated_specs = _prompt_chapter_elements(specs)

    assert printed_messages == [
        "Elementen zijn figuren of tabellen die in dit hoofdstuk gebruikt mogen worden.\n"
        "Je kunt deze stap overslaan met \"klaar\".",
        "Elementen zijn figuren of tabellen die in dit hoofdstuk gebruikt mogen worden.\n"
        "Je kunt deze stap overslaan met \"klaar\".",
    ]
    assert choice_calls == [
        ("Element toevoegen", ["figuur", "tabel", "klaar"]),
        ("Element toevoegen", ["figuur", "tabel", "klaar"]),
        ("Element toevoegen", ["figuur", "tabel", "klaar"]),
        ("Element toevoegen", ["figuur", "tabel", "klaar"]),
    ]
    assert updated_specs[0].elements == [plot, table]
    assert updated_specs[1].elements == []
    assert specs[0].elements == []
    assert len(specs[1].elements) == 1


def test_prompt_report_inputs_collects_config_specs_pointers_and_elements(monkeypatch) -> None:
    calls: list[str] = []
    config = object()
    outline_specs = [ChapterSpec(role=ChapterRole.INTRODUCTION, title="Inleiding")]
    pointer_specs = [
        ChapterSpec(
            role=ChapterRole.INTRODUCTION,
            title="Inleiding",
            pointers=["Beschrijf het doel."],
        )
    ]
    element_specs = [
        pointer_specs[0].model_copy(
            update={
                "elements": [
                    Plot(caption="Zakking", path="missing.png", validate_path_exists=False)
                ]
            }
        )
    ]

    def fake_prompt_report_config():
        calls.append("config")
        return config

    def fake_prompt_chapter_specs():
        calls.append("specs")
        return outline_specs

    def fake_prompt_chapter_pointers(specs):
        calls.append("pointers")
        assert specs is outline_specs
        return pointer_specs

    def fake_prompt_chapter_elements(specs):
        calls.append("elements")
        assert specs is pointer_specs
        return element_specs

    monkeypatch.setattr("forelius.interactive._prompt_report_config", fake_prompt_report_config)
    monkeypatch.setattr("forelius.interactive._prompt_chapter_specs", fake_prompt_chapter_specs)
    monkeypatch.setattr("forelius.interactive._prompt_chapter_pointers", fake_prompt_chapter_pointers)
    monkeypatch.setattr("forelius.interactive._prompt_chapter_elements", fake_prompt_chapter_elements)

    collected_config, collected_specs = _prompt_report_inputs()

    assert calls == ["config", "specs", "pointers", "elements"]
    assert collected_config is config
    assert collected_specs is element_specs


def test_review_chapter_drafts_accepts_draft(monkeypatch) -> None:
    config = make_config()
    specs = [ChapterSpec(role=ChapterRole.BODY, title="Resultaten")]
    section = Section(
        chapter=ChapterRef(number=1, title="Resultaten"),
        text="# Resultaten",
        line_element_map={},
    )
    printed_messages: list[str] = []
    generator_calls: list[tuple[ReportConfig, list[ChapterSpec], GenerationOrder]] = []

    class FakeDraft:
        def current(self) -> Section:
            return section

        def pointers(self) -> list[str]:
            return ["Bespreek de resultaten."]

        def accept(self) -> Section:
            return section

    class FakeGenerator:
        chapter = ChapterRef(number=1, title="Resultaten")

        def draft(self) -> FakeDraft:
            return FakeDraft()

    def fake_chapter_generators(config_arg, specs_arg, generation_order):
        generator_calls.append((config_arg, specs_arg, generation_order))
        return iter([FakeGenerator()])

    monkeypatch.setattr("forelius.interactive.chapter_generators", fake_chapter_generators)
    monkeypatch.setattr("forelius.interactive._prompt_choice", lambda label, choices: "accepteren")
    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )

    accepted_sections = _review_chapter_drafts(config, specs)

    assert generator_calls == [(config, specs, GenerationOrder.REPORT)]
    assert accepted_sections == [section]
    assert printed_messages == [
        "Concept voor \"Resultaten\" wordt gegenereerd...",
        "────────────────────────────────────────",
        "Review — Resultaten",
        "────────────────────────────────────────",
        "Lees het concept hieronder. Kies daarna accepteren, herzien of afbreken.",
        "Concept voor hoofdstuk: Resultaten",
        "# Resultaten",
        "Bestaande pointers:",
        "- Bespreek de resultaten.",
    ]


def test_review_chapter_drafts_revises_then_accepts_with_updated_pointers(monkeypatch) -> None:
    section = Section(
        chapter=ChapterRef(number=1, title="Resultaten"),
        text="# Resultaten",
        line_element_map={},
    )
    revised_section = Section(
        chapter=ChapterRef(number=1, title="Resultaten"),
        text="# Revised Results",
        line_element_map={},
    )
    printed_messages: list[str] = []
    actions = iter(["herzien", "accepteren"])
    feedback_values: list[str] = []

    class FakeDraft:
        def __init__(self) -> None:
            self._section = section
            self._pointers = ["Bespreek de resultaten."]

        def current(self) -> Section:
            return self._section

        def pointers(self) -> list[str]:
            return list(self._pointers)

        def revise(self, pointers: list[str]) -> Section:
            feedback_values.extend(pointers)
            self._pointers.extend(pointers)
            self._section = revised_section
            return revised_section

        def accept(self) -> Section:
            return self._section

    class FakeGenerator:
        chapter = ChapterRef(number=1, title="Resultaten")

        def draft(self) -> FakeDraft:
            return FakeDraft()

    monkeypatch.setattr(
        "forelius.interactive.chapter_generators",
        lambda config, specs, generation_order: iter([FakeGenerator()]),
    )
    monkeypatch.setattr("forelius.interactive._prompt_choice", lambda label, choices: next(actions))
    yes_no_calls: list[tuple[str, bool]] = []
    yes_no_values = iter([False])

    def fake_prompt_yes_no(label: str, default: bool = False) -> bool:
        yes_no_calls.append((label, default))
        return next(yes_no_values)

    monkeypatch.setattr("forelius.interactive._prompt_yes_no", fake_prompt_yes_no)
    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        lambda label: "Voeg de maatgevende waarde toe.",
    )
    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )

    accepted_sections = _review_chapter_drafts(make_config(), [])

    assert accepted_sections == [revised_section]
    assert feedback_values == ["Voeg de maatgevende waarde toe."]
    assert yes_no_calls == [("Nog een pointer voor herziening toevoegen?", False)]
    assert printed_messages == [
        "Concept voor \"Resultaten\" wordt gegenereerd...",
        "────────────────────────────────────────",
        "Review — Resultaten",
        "────────────────────────────────────────",
        "Lees het concept hieronder. Kies daarna accepteren, herzien of afbreken.",
        "Concept voor hoofdstuk: Resultaten",
        "# Resultaten",
        "Bestaande pointers:",
        "- Bespreek de resultaten.",
        "Huidige pointers voor dit hoofdstuk:",
        "Bestaande pointers:",
        "- Bespreek de resultaten.",
        "Concept voor hoofdstuk: Resultaten",
        "# Revised Results",
        "Bestaande pointers:",
        "- Bespreek de resultaten.",
        "- Voeg de maatgevende waarde toe.",
    ]


def test_review_chapter_drafts_raises_when_aborted(monkeypatch) -> None:
    section = Section(
        chapter=ChapterRef(number=1, title="Resultaten"),
        text="# Resultaten",
        line_element_map={},
    )

    class FakeDraft:
        def current(self) -> Section:
            return section

        def pointers(self) -> list[str]:
            return []

    class FakeGenerator:
        chapter = ChapterRef(number=1, title="Resultaten")

        def draft(self) -> FakeDraft:
            return FakeDraft()

    monkeypatch.setattr(
        "forelius.interactive.chapter_generators",
        lambda config, specs, generation_order: iter([FakeGenerator()]),
    )
    monkeypatch.setattr("forelius.interactive._prompt_choice", lambda label, choices: "afbreken")
    monkeypatch.setattr("forelius.interactive._print_message", lambda message: None)

    with pytest.raises(InteractiveReportAborted, match="aborted"):
        _review_chapter_drafts(make_config(), [])


def test_prompt_for_report_prompts_and_reviews_each_chapter_after_outline(monkeypatch) -> None:
    config = make_config()
    initial_specs = [
        ChapterSpec(role=ChapterRole.INTRODUCTION, title="Inleiding"),
        ChapterSpec(role=ChapterRole.BODY, title="Resultaten"),
    ]
    sections = [
        Section(
            chapter=ChapterRef(number=1, title="Inleiding"),
            text="# Inleiding",
            line_element_map={},
        ),
        Section(
            chapter=ChapterRef(number=2, title="Resultaten"),
            text="# Resultaten",
            line_element_map={},
        ),
    ]
    ordered_sections = list(sections)
    printed_messages: list[str] = []
    calls: list[str] = []

    class FakeGenerator:
        def __init__(self, index: int) -> None:
            self.index = index

    class FakeRenderer:
        def render(self, render_config, render_sections):
            calls.append("render")
            assert render_config is config
            assert render_sections is ordered_sections
            return "# Markdown"

    def fake_prompt_report_config():
        calls.append("config")
        return config

    def fake_prompt_chapter_specs():
        calls.append("outline")
        return list(initial_specs)

    def fake_prompt_pointers_for_chapter(spec):
        calls.append(f"pointers:{spec.title}")
        return spec.model_copy(update={"pointers": [f"Pointer voor {spec.title}"]})

    def fake_prompt_elements_for_chapter(spec):
        calls.append(f"elements:{spec.title}")
        return spec

    def fake_chapter_generators(config_arg, specs_arg, generation_order):
        calls.append("generators")
        assert config_arg is config
        assert generation_order is GenerationOrder.REPORT
        assert any(spec.pointers for spec in specs_arg)
        return iter([FakeGenerator(index) for index, _ in enumerate(specs_arg)])

    def fake_review_chapter_draft(generator):
        calls.append(f"review:{generator.index}")
        return sections[generator.index]

    def fake_order_sections(sections_arg, generation_order):
        calls.append("order")
        assert sections_arg == sections
        assert generation_order is GenerationOrder.REPORT
        return ordered_sections

    monkeypatch.setattr("forelius.interactive._prompt_report_config", fake_prompt_report_config)
    monkeypatch.setattr("forelius.interactive._prompt_chapter_specs", fake_prompt_chapter_specs)
    monkeypatch.setattr("forelius.interactive._prompt_pointers_for_chapter", fake_prompt_pointers_for_chapter)
    monkeypatch.setattr("forelius.interactive._prompt_elements_for_chapter", fake_prompt_elements_for_chapter)
    monkeypatch.setattr("forelius.interactive.chapter_generators", fake_chapter_generators)
    monkeypatch.setattr("forelius.interactive._review_chapter_draft", fake_review_chapter_draft)
    monkeypatch.setattr("forelius.interactive.order_sections", fake_order_sections)
    monkeypatch.setattr("forelius.interactive.MarkdownRenderer", FakeRenderer)
    monkeypatch.setattr(
        "forelius.interactive._print_message",
        lambda message: printed_messages.append(message),
    )

    markdown = prompt_for_report()

    assert calls == [
        "config",
        "outline",
        "pointers:Inleiding",
        "elements:Inleiding",
        "generators",
        "review:0",
        "pointers:Resultaten",
        "elements:Resultaten",
        "generators",
        "review:1",
        "order",
        "render",
    ]
    assert markdown == "# Markdown"
    assert printed_messages == [
        "────────────────────────────────────────",
        "Forelius interactief rapport",
        "────────────────────────────────────────",
        "We verzamelen eerst de basisgegevens en hoofdstukindeling.\n"
        "Daarna werken we hoofdstuk voor hoofdstuk uit.",
        "────────────────────────────────────────",
        "Stap 3/3 — Hoofdstukken uitwerken",
        "────────────────────────────────────────",
        "We werken elk hoofdstuk apart uit. Per hoofdstuk voeg je eerst pointers\n"
        "en optionele elementen toe. Daarna wordt een concept gegenereerd.",
        "────────────────────────────────────────",
        "Hoofdstuk 1/2 — Inleiding",
        "────────────────────────────────────────",
        "────────────────────────────────────────",
        "Hoofdstuk 2/2 — Resultaten",
        "────────────────────────────────────────",
        "────────────────────────────────────────",
        "Rapport voltooid",
        "────────────────────────────────────────",
        "Alle hoofdstukken zijn geaccepteerd. Hieronder staat de Markdown-output.",
        "# Markdown",
    ]


def test_prompt_report_config_uses_dutch_labels_and_defaults(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []
    values = iter([
        "geotechnisch ingenieur",
        "paalfundering",
        "Nederlands",
        "Figuur",
        "Tabel",
    ])

    def fake_prompt_required_text(label: str, default: str | None = None) -> str:
        calls.append((label, default))
        return next(values)

    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        fake_prompt_required_text,
    )

    config = _prompt_report_config()

    assert calls == [
        ("Discipline", None),
        ("Onderwerp", None),
        ("Taal", None),
        ("Figuurlabel", "Figuur"),
        ("Tabellabel", "Tabel"),
    ]
    assert config.discipline == "geotechnisch ingenieur"
    assert config.subject == "paalfundering"
    assert config.language == "Nederlands"
    assert config.figure_label == "Figuur"
    assert config.table_label == "Tabel"


def test_prompt_report_config_uses_english_label_defaults(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []
    values = iter([
        "geotechnical engineer",
        "pile foundation design",
        "English",
        "Figure",
        "Table",
    ])

    def fake_prompt_required_text(label: str, default: str | None = None) -> str:
        calls.append((label, default))
        return next(values)

    monkeypatch.setattr(
        "forelius.interactive._prompt_required_text",
        fake_prompt_required_text,
    )

    config = _prompt_report_config()

    assert calls[-2:] == [("Figuurlabel", "Figure"), ("Tabellabel", "Table")]
    assert config.language == "English"
    assert config.figure_label == "Figure"
    assert config.table_label == "Table"


def test_parse_csv_table_parses_headers_and_rows() -> None:
    headers, rows = _parse_csv_table("Case,Load\nA,10 kN\nB,20 kN")

    assert headers == ["Case", "Load"]
    assert rows == [["A", "10 kN"], ["B", "20 kN"]]


def test_parse_csv_table_supports_quoted_commas() -> None:
    headers, rows = _parse_csv_table('Case,Description\nA,"service, limit"')

    assert headers == ["Case", "Description"]
    assert rows == [["A", "service, limit"]]


def test_parse_csv_table_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="CSV input must not be empty"):
        _parse_csv_table("  \n  ")


def test_parse_csv_table_rejects_missing_data_rows() -> None:
    with pytest.raises(ValueError, match="at least one data row"):
        _parse_csv_table("Case,Load")


def test_parse_csv_table_rejects_empty_header_value() -> None:
    with pytest.raises(ValueError, match="CSV header contains an empty value at position 2"):
        _parse_csv_table("Case,\nA,10 kN")


def test_parse_csv_table_rejects_empty_data_row() -> None:
    with pytest.raises(ValueError, match="CSV row 2 must not be empty"):
        _parse_csv_table("Case,Load\n\nA,10 kN")


def test_parse_csv_table_rejects_empty_cell_value() -> None:
    with pytest.raises(ValueError, match="CSV row 2 contains an empty value at position 2"):
        _parse_csv_table("Case,Load\nA,")


def test_parse_csv_table_rejects_wrong_row_length() -> None:
    with pytest.raises(ValueError, match=r"CSV row 2 has 1 value\(s\); expected 2"):
        _parse_csv_table("Case,Load\nA")
