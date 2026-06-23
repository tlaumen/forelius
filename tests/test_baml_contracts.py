from pathlib import Path

BAML_ROOT = Path("baml_src")
REPORT_ROOT = BAML_ROOT / "report"
PLOTTING_ROOT = BAML_ROOT / "plotting"


def read_baml(relative_path: str) -> str:
    return (BAML_ROOT / relative_path).read_text()


def test_clients_use_claude_haiku_45_and_anthropic_env_var() -> None:
    source = read_baml("clients.baml")

    assert "client<llm> ForeliusClaudeHaiku45" in source
    assert "provider anthropic" in source
    assert 'model "claude-haiku-4-5-20251001"' in source
    assert "api_key env.ANTHROPIC_API_KEY" in source


def test_shared_schema_uses_flat_pointers_and_required_element_fields() -> None:
    source = read_baml("report/shared.baml")

    assert "class ChapterInput" in source
    assert "pointers string[]" in source
    for field in [
        "element_id string",
        "kind string",
        "caption string",
        "placement_token string",
        "reference_token string",
    ]:
        assert field in source


def test_shared_prompt_core_contains_required_token_instructions() -> None:
    source = read_baml("report/shared.baml")

    assert "template_string SharedReportPromptCore" in source
    assert "exactly one top-level Markdown chapter header" in source
    assert "placement tokens on their own line" in source
    assert "inline reference tokens" in source
    assert "Do not invent visible figure/table numbering" in source
    assert "Do not render tables or figures yourself" in source
    assert "Do not include Markdown image syntax" in source
    assert "Do not include Markdown table syntax" in source


def test_every_report_function_exists_and_uses_shared_prompt_core() -> None:
    expected = {
        "report/introduction.baml": "ReportIntroduction",
        "report/chapter.baml": "ReportChapter",
        "report/conclusion.baml": "ReportConclusion",
    }

    for relative_path, function_name in expected.items():
        source = read_baml(relative_path)
        assert f"function {function_name}(input: ChapterInput) -> string" in source
        assert "client ForeliusClaudeHaiku45" in source
        assert "{{ SharedReportPromptCore(input) }}" in source


def test_every_report_function_has_at_least_two_baml_native_tests() -> None:
    expected = {
        "report/introduction.baml": "ReportIntroduction",
        "report/chapter.baml": "ReportChapter",
        "report/conclusion.baml": "ReportConclusion",
    }

    for relative_path, function_name in expected.items():
        source = read_baml(relative_path)
        assert source.count("test ") >= 2
        assert source.count(f"functions [{function_name}]") >= 2


def test_representative_baml_fixture_inputs_exist_for_each_function() -> None:
    fixture_root = Path("tests/fixtures/baml")

    for function_name in [
        "report_introduction",
        "report_chapter",
        "report_conclusion",
    ]:
        fixtures = sorted(fixture_root.glob(f"{function_name}_*.json"))
        assert len(fixtures) >= 2


def test_plotting_baml_files_exist() -> None:
    for relative_path in [
        "plotting/shared.baml",
        "plotting/extraction.baml",
        "plotting/intent.baml",
        "plotting/revision.baml",
    ]:
        assert (BAML_ROOT / relative_path).exists()


def test_plotting_shared_schema_declares_required_enums_and_models() -> None:
    source = read_baml("plotting/shared.baml")

    for enum_name in [
        "ExtractionConfidence",
        "ExtractedDataType",
        "PlotGrid",
        "PlotLineStyle",
        "PlotMarker",
    ]:
        assert f"enum {enum_name}" in source

    for model_name in [
        "ExtractedColumn",
        "ExtractedDataset",
        "DatasetColumnMetadata",
        "DatasetMetadata",
        "XYPlotOptions",
        "XYPlotIntent",
        "CreateXYPlotIntentInput",
        "ReviseXYPlotIntentInput",
    ]:
        assert f"class {model_name}" in source

    assert "grid PlotGrid" in source
    assert "line_style PlotLineStyle" in source
    assert "marker PlotMarker" in source
    assert "value_count" not in source
    assert "finite_count" not in source
    assert "ignored_count" not in source
    assert "sample_values" not in source


def test_every_plotting_function_exists_and_uses_claude_haiku_45() -> None:
    expected = {
        "plotting/extraction.baml": "function ExtractDatasetFromFreeform(numbered_input: string) -> ExtractedDataset",
        "plotting/intent.baml": "function CreateXYPlotIntent(input: CreateXYPlotIntentInput) -> XYPlotIntent",
        "plotting/revision.baml": "function ReviseXYPlotIntent(input: ReviseXYPlotIntentInput) -> XYPlotIntent",
    }

    for relative_path, function_signature in expected.items():
        source = read_baml(relative_path)
        assert function_signature in source
        assert "client ForeliusClaudeHaiku45" in source


def test_plotting_prompts_include_safety_constraints() -> None:
    extraction = read_baml("plotting/extraction.baml")
    intent = read_baml("plotting/intent.baml")
    revision = read_baml("plotting/revision.baml")

    assert "Do not invent rows, columns, values" in extraction
    assert "Preserve original value strings exactly" in extraction
    assert "Do not generate code" in extraction
    shared = read_baml("plotting/shared.baml")

    assert "Do not invent columns, rows, values" in shared
    assert "Do not generate code" in shared
    assert "Revise only the plot intent" in revision
    assert "Preserve current settings unless" in revision
    assert "Do not generate code" in revision


def test_plotting_intent_inputs_use_metadata_not_full_numeric_arrays() -> None:
    source = read_baml("plotting/shared.baml")

    assert "dataset DatasetMetadata" in source
    assert "numeric_values" not in source
    assert "values float[]" not in source


def test_every_plotting_function_has_at_least_two_baml_native_tests() -> None:
    expected = {
        "plotting/extraction.baml": "ExtractDatasetFromFreeform",
        "plotting/intent.baml": "CreateXYPlotIntent",
        "plotting/revision.baml": "ReviseXYPlotIntent",
    }

    for relative_path, function_name in expected.items():
        source = read_baml(relative_path)
        assert source.count("test ") >= 2
        assert source.count(f"functions [{function_name}]") >= 2
