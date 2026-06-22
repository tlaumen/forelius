import csv
from io import StringIO
from pathlib import Path

from prompt_toolkit import print_formatted_text, prompt
from prompt_toolkit.shortcuts import choice

from forelius.chapter import ChapterRole, ChapterSpec
from forelius.config import ReportConfig
from forelius.elements import Plot, Table
from forelius.generator import ChapterGenerator, GenerationOrder, chapter_generators, order_sections
from forelius.render import MarkdownRenderer
from forelius.section import Section


_CHAPTER_ROLE_CHOICES = {
    "inleiding": ChapterRole.INTRODUCTION,
    "conclusie": ChapterRole.CONCLUSION,
    "ander hoofdstuk": ChapterRole.BODY,
}

_ELEMENT_CHOICES = {
    "figuur": "figure",
    "tabel": "table",
    "klaar": "done",
}

_REVIEW_ACTION_CHOICES = {
    "accepteren": "accept",
    "herzien": "revise",
    "afbreken": "abort",
}

_SEPARATOR = "────────────────────────────────────────"

_LABEL_DEFAULTS_BY_LANGUAGE = {
    "nederlands": ("Figuur", "Tabel"),
    "dutch": ("Figuur", "Tabel"),
    "english": ("Figure", "Table"),
    "engels": ("Figure", "Table"),
}


class InteractiveReportAborted(Exception):
    """Raised when the user aborts the interactive report flow."""


def _parse_csv_table(value: str) -> tuple[list[str], list[list[str]]]:
    if not value.strip():
        raise ValueError("CSV input must not be empty")

    try:
        parsed_rows = list(csv.reader(StringIO(value), strict=True))
    except csv.Error as error:
        raise ValueError(f"Invalid CSV input: {error}") from error

    if not parsed_rows:
        raise ValueError("CSV input must include a header row")

    headers = _normalize_csv_row(parsed_rows[0], row_number=1, row_name="CSV header")
    data_rows = parsed_rows[1:]
    if not data_rows:
        raise ValueError("CSV input must include at least one data row")

    rows: list[list[str]] = []
    for index, row in enumerate(data_rows, start=2):
        normalized_row = _normalize_csv_row(row, row_number=index, row_name=f"CSV row {index}")
        if len(normalized_row) != len(headers):
            raise ValueError(
                f"CSV row {index} has {len(normalized_row)} value(s); "
                f"expected {len(headers)}"
            )
        rows.append(normalized_row)

    return headers, rows


def _normalize_csv_row(row: list[str], row_number: int, row_name: str) -> list[str]:
    if not row or all(not cell.strip() for cell in row):
        raise ValueError(f"{row_name} must not be empty")

    normalized = [cell.strip() for cell in row]
    for position, cell in enumerate(normalized, start=1):
        if not cell:
            raise ValueError(
                f"{row_name} contains an empty value at position {position}"
            )

    return normalized


def _print_message(message: str) -> None:
    print_formatted_text(message)


def _print_section(title: str, description: str | None = None) -> None:
    _print_message(_SEPARATOR)
    _print_message(title)
    _print_message(_SEPARATOR)
    if description:
        _print_message(description)


def _print_numbered_specs(specs: list[ChapterSpec]) -> None:
    _print_message("Hoofdstukken:")
    for index, spec in enumerate(specs, start=1):
        _print_message(f"{index}. {spec.title}")


def _prompt_required_text(label: str, default: str | None = None) -> str:
    while True:
        prompt_label = f"{label} [{default}]" if default is not None else label
        value = prompt(f"{prompt_label}: ").strip()
        if value:
            return value
        if default is not None:
            return default

        _print_message(f"{label} is required")


def _prompt_choice(label: str, choices: list[str]) -> str:
    if not choices:
        raise ValueError("choices must not be empty")

    normalized_choices = [item.strip() for item in choices]
    if any(not item for item in normalized_choices):
        raise ValueError("choices must not contain empty values")

    return choice(
        message=f"{label}:",
        options=[(item, item) for item in normalized_choices],
    )


def _prompt_yes_no(label: str, default: bool = False) -> bool:
    default_hint = "Y/n" if default else "y/N"
    while True:
        value = prompt(f"{label} [{default_hint}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False

        _print_message("Enter yes or no")


def _label_defaults_for_language(language: str) -> tuple[str | None, str | None]:
    return _LABEL_DEFAULTS_BY_LANGUAGE.get(language.strip().lower(), (None, None))


def _prompt_report_config() -> ReportConfig:
    _print_section(
        "Stap 1/3 — Rapportinstellingen",
        "Vul de algemene instellingen in voor het rapport.",
    )
    discipline = _prompt_required_text("Discipline")
    subject = _prompt_required_text("Onderwerp")
    language = _prompt_required_text("Taal")
    figure_label_default, table_label_default = _label_defaults_for_language(language)

    return ReportConfig(
        discipline=discipline,
        subject=subject,
        language=language,
        figure_label=_prompt_required_text("Figuurlabel", default=figure_label_default),
        table_label=_prompt_required_text("Tabellabel", default=table_label_default),
    )


def _prompt_chapter_spec() -> ChapterSpec:
    title = _prompt_required_text("Hoofdstuktitel")
    role_label = _prompt_choice("Soort hoofdstuk", list(_CHAPTER_ROLE_CHOICES))
    pointers: list[str] = []

    while _prompt_yes_no("Pointer toevoegen?", default=True):
        pointers.append(_prompt_required_text("Pointer"))

    return ChapterSpec(
        role=_CHAPTER_ROLE_CHOICES[role_label],
        title=title,
        pointers=pointers,
    )


def _prompt_chapter_specs() -> list[ChapterSpec]:
    _print_section(
        "Stap 2/3 — Hoofdstukindeling",
        "Het rapport krijgt automatisch een Inleiding en Conclusie.\n"
        "Voeg hieronder de tussenliggende hoofdstukken toe.",
    )
    specs = [ChapterSpec(role=ChapterRole.INTRODUCTION, title="Inleiding")]

    while True:
        specs.append(
            ChapterSpec(
                role=ChapterRole.BODY,
                title=_prompt_required_text("Hoofdstuktitel"),
            )
        )
        if not _prompt_yes_no("Nog een hoofdstuk toevoegen?", default=True):
            break

    specs.append(ChapterSpec(role=ChapterRole.CONCLUSION, title="Conclusie"))
    _print_numbered_specs(specs)
    return specs


def _prompt_pointers(
    add_label: str,
    pointer_label: str,
    next_add_label: str,
    first_default: bool,
    require_one: bool,
) -> list[str]:
    pointers: list[str] = []

    if require_one:
        pointers.append(_prompt_required_text(pointer_label))
        while _prompt_yes_no(next_add_label, default=False):
            pointers.append(_prompt_required_text(pointer_label))
        return pointers

    current_add_label = add_label
    current_default = first_default
    while _prompt_yes_no(current_add_label, default=current_default):
        pointers.append(_prompt_required_text(pointer_label))
        current_add_label = next_add_label
        current_default = False

    return pointers


def _prompt_pointers_for_chapter(spec: ChapterSpec) -> ChapterSpec:
    _print_message(
        "Pointers zijn inhoudelijke aanwijzingen voor de generator.\n"
        "Voorbeeld: \"Leg het doel en de scope van het rapport uit.\""
    )
    pointers = _prompt_pointers(
        add_label="Pointer toevoegen?",
        pointer_label="Pointer",
        next_add_label="Nog een pointer toevoegen?",
        first_default=True,
        require_one=False,
    )
    return spec.model_copy(update={"pointers": pointers})


def _prompt_chapter_pointers(specs: list[ChapterSpec]) -> list[ChapterSpec]:
    return [_prompt_pointers_for_chapter(spec) for spec in specs]


def _prompt_figure() -> Plot:
    caption = _prompt_required_text("Figuurbijschrift")
    path = Path(_prompt_required_text("Figuurpad"))
    if not path.exists():
        _print_message(f"Waarschuwing: figuurpad bestaat niet: {path}")

    return Plot(caption=caption, path=path, validate_path_exists=False)


def _prompt_table() -> Table:
    caption = _prompt_required_text("Tabelbijschrift")
    while True:
        csv_value = prompt("Plak CSV-tabel: ", multiline=True)
        try:
            headers, rows = _parse_csv_table(csv_value)
        except ValueError as error:
            _print_message(str(error))
            continue

        return Table(caption=caption, headers=headers, rows=rows)


def _prompt_elements_for_chapter(spec: ChapterSpec) -> ChapterSpec:
    _print_message(
        "Elementen zijn figuren of tabellen die in dit hoofdstuk gebruikt mogen worden.\n"
        "Je kunt deze stap overslaan met \"klaar\"."
    )
    elements: list[Plot | Table] = []
    while True:
        selected = _prompt_choice("Element toevoegen", list(_ELEMENT_CHOICES))
        element_kind = _ELEMENT_CHOICES[selected]
        if element_kind == "done":
            break
        if element_kind == "figure":
            elements.append(_prompt_figure())
        elif element_kind == "table":
            elements.append(_prompt_table())

    return spec.model_copy(update={"elements": elements})


def _prompt_chapter_elements(specs: list[ChapterSpec]) -> list[ChapterSpec]:
    return [_prompt_elements_for_chapter(spec) for spec in specs]


def _prompt_report_inputs() -> tuple[ReportConfig, list[ChapterSpec]]:
    config = _prompt_report_config()
    specs = _prompt_chapter_specs()
    specs = _prompt_chapter_pointers(specs)
    specs = _prompt_chapter_elements(specs)
    return config, specs


def _print_draft(chapter_title: str, text: str) -> None:
    _print_message(f"Concept voor hoofdstuk: {chapter_title}")
    _print_message(text)


def _print_pointers(pointers: list[str]) -> None:
    if not pointers:
        _print_message("Bestaande pointers: geen")
        return

    _print_message("Bestaande pointers:")
    for pointer in pointers:
        _print_message(f"- {pointer}")


def _review_chapter_draft(generator: ChapterGenerator) -> Section:
    _print_message(f"Concept voor \"{generator.chapter.title}\" wordt gegenereerd...")
    draft = generator.draft()
    _print_section(
        f"Review — {generator.chapter.title}",
        "Lees het concept hieronder. Kies daarna accepteren, herzien of afbreken.",
    )
    _print_draft(generator.chapter.title, draft.current().text)

    while True:
        _print_pointers(draft.pointers())
        selected = _prompt_choice("Actie", list(_REVIEW_ACTION_CHOICES))
        action = _REVIEW_ACTION_CHOICES[selected]

        if action == "accept":
            return draft.accept()
        if action == "revise":
            _print_message("Huidige pointers voor dit hoofdstuk:")
            _print_pointers(draft.pointers())
            revision_pointers = _prompt_pointers(
                add_label="Pointer voor herziening toevoegen?",
                pointer_label="Pointer voor herziening",
                next_add_label="Nog een pointer voor herziening toevoegen?",
                first_default=True,
                require_one=True,
            )
            revised = draft.revise(revision_pointers)
            _print_draft(generator.chapter.title, revised.text)
            continue
        if action == "abort":
            raise InteractiveReportAborted("Interactive report flow aborted")


def _review_chapter_drafts(config: ReportConfig, specs: list[ChapterSpec]) -> list[Section]:
    return [
        _review_chapter_draft(generator)
        for generator in chapter_generators(
            config,
            specs,
            generation_order=GenerationOrder.REPORT,
        )
    ]


def prompt_for_report() -> str:
    """Interactively collect report inputs, generate chapters, and return Markdown."""
    _print_section(
        "Forelius interactief rapport",
        "We verzamelen eerst de basisgegevens en hoofdstukindeling.\n"
        "Daarna werken we hoofdstuk voor hoofdstuk uit.",
    )
    config = _prompt_report_config()
    specs = _prompt_chapter_specs()
    accepted_sections: list[Section] = []

    _print_section(
        "Stap 3/3 — Hoofdstukken uitwerken",
        "We werken elk hoofdstuk apart uit. Per hoofdstuk voeg je eerst pointers\n"
        "en optionele elementen toe. Daarna wordt een concept gegenereerd.",
    )

    for index, spec in enumerate(specs):
        _print_section(f"Hoofdstuk {index + 1}/{len(specs)} — {spec.title}")
        spec = _prompt_pointers_for_chapter(spec)
        spec = _prompt_elements_for_chapter(spec)
        specs[index] = spec
        generator = list(
            chapter_generators(
                config,
                specs,
                generation_order=GenerationOrder.REPORT,
            )
        )[index]
        accepted_sections.append(_review_chapter_draft(generator))

    ordered_sections = order_sections(accepted_sections, GenerationOrder.REPORT)
    markdown = MarkdownRenderer().render(config, ordered_sections)
    _print_section(
        "Rapport voltooid",
        "Alle hoofdstukken zijn geaccepteerd. Hieronder staat de Markdown-output.",
    )
    _print_message(markdown)
    return markdown
