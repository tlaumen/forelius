# Design: Minimal Prompt Toolkit Interactive Report Flow

## Summary

Add a minimal interactive Python function that uses `prompt_toolkit` primitives to collect report configuration, chapters, pointers, and optional figure/table elements from a user; generate each chapter draft; loop over revise/accept decisions; and return the final rendered Markdown report.

This is not a full CLI application, not a full-screen TUI, and not a web interface. The intended first interface is one callable function:

```python
from forelius import prompt_for_report

markdown = prompt_for_report()
```

The implementation should be additive and should preserve the existing generation, BAML, section parsing, and rendering behavior unless the requested interactive flow reveals a real incompatibility. The main non-additive model change is configurable figure path validation for `Plot`, so interactive and manual end-to-end flows can use placeholder paths while existing strict validation remains available.

## Goals

- Provide one simple user-callable interactive report function.
- Use `prompt_toolkit`, not Python primitive `input()`.
- Prompt for report configuration:
  - discipline;
  - subject;
  - language;
  - figure label;
  - table label.
- Prompt for chapters:
  - title;
  - role;
  - pointers;
  - optional figure/table elements.
- Generate drafts using existing `ChapterGenerator` / `ChapterDraft` behavior.
- After each generated draft, loop until the user accepts, revises with feedback, or aborts.
- Render accepted sections to Markdown using the existing `MarkdownRenderer`.
- Return the final Markdown string.
- Add a manual end-to-end script outside `tests/` for full interactive validation.
- Keep normal automated tests offline and non-interactive.

## Non-Goals

- No full CLI command or console script is required.
- No full-screen TUI.
- No web interface in this change.
- No generic interface abstraction framework.
- No changes to BAML prompt behavior unless required by the existing generation API.
- No report-level revision loop.
- No file output/write prompt in the first implementation.
- No live LLM calls in automated tests.
- No automated tests that block on terminal input.

## Existing Codebase Context

Repository reconnaissance found an existing small Python package with clear module boundaries:

- `forelius/config.py`
  - Defines `ChapterRef` and `ReportConfig`.
- `forelius/chapter.py`
  - Defines `ChapterRole` and `ChapterSpec`.
  - `ChapterSpec.with_feedback()` appends feedback to pointers.
- `forelius/elements.py`
  - Defines `Plot`, `Table`, `ReportElement`, `ResolvedElement`, and `ElementRegistry`.
  - `Plot` currently requires `path` to exist via validation.
  - `Table` validates row lengths.
- `forelius/section.py`
  - Defines `Section`, token regexes, `SectionParseError`, and `parse_section()`.
- `forelius/generator.py`
  - Defines `GenerationOrder`, `ChapterGenerator`, `ChapterDraft`, `chapter_generators()`, `order_sections()`, and `generate_report()`.
  - `ChapterDraft` already supports initial draft generation, revision, and acceptance.
- `forelius/render/markdown.py`
  - Defines `MarkdownRenderer`, which renders sections to Markdown and embeds figure paths without reading files.
- `forelius/initialization.py`
  - Handles required environment validation for real BAML calls.
- `forelius/__init__.py`
  - Exports the current public API.

Current dependencies in `pyproject.toml` include:

- `baml-py`
- `pydantic`

Current dev dependency:

- `pytest`

Current validation commands documented in `README.md`:

```bash
uv run pytest
uv run baml-cli check
uv run baml-cli generate
```

Normal tests are designed to avoid live LLM calls.

## Relevant Files and Modules

Existing files to update:

- `pyproject.toml`
- `forelius/__init__.py`
- `forelius/elements.py`
- `tests/test_exports.py`
- `tests/test_models.py`

New files to add:

- `forelius/interactive.py`
- `tests/test_interactive.py`
- `e2e/manual_prompt_for_report.py`

Existing files intentionally reused without behavior changes:

- `forelius/generator.py`
- `forelius/chapter.py`
- `forelius/config.py`
- `forelius/render/markdown.py`
- `forelius/section.py`

## Accepted Design Decisions

### Decision 1: Function boundary and public API

Status: Accepted.

Add a new module `forelius/interactive.py` with one public function:

```python
def prompt_for_report() -> str: ...
```

Export `prompt_for_report` from `forelius/__init__.py`.

### Decision 2: Prompt flow

Status: Accepted with user modification.

Use `prompt_toolkit` to prompt for report config, chapters, roles, pointers, and elements. Do not use primitive `input()`.

### Decision 3: Draft/revision/acceptance loop

Status: Accepted.

After each chapter draft is generated, enter a per-chapter loop that shows the current draft and lets the user accept, revise with feedback, or abort. If the user aborts, raise a custom `InteractiveReportAborted` exception from `forelius.interactive` rather than returning partial Markdown.

### Decision 4: Element prompting

Status: Accepted with user modification.

For each chapter, prompt whether to add an element and which type:

1. choose `figure`, `table`, or `done`;
2. prompt caption;
3. for a figure, prompt path;
4. for a table, prompt headers and rows.

### Decision 5: Return/output behavior

Status: Accepted.

After all chapters are accepted, order sections, render Markdown, display the final Markdown with `prompt_toolkit.print_formatted_text()`, and return it as `str`. Do not write files.

### Decision 6: Dependency and automated tests

Status: Accepted.

Add `prompt-toolkit>=3` as a normal project dependency. Import and use `prompt_toolkit` in Python code. Keep automated tests focused on import/export and pure helper behavior. Do not add automated terminal-input or live-LLM tests.

### Decision 7: Figure path validation policy

Status: Accepted with Option C.

Add configurable `Plot` path validation. Preserve strict existence validation by default, but allow callers to disable it with a field such as:

```python
validate_path_exists: bool = True
```

The interactive report flow must construct figures with strict validation disabled:

```python
Plot(caption=caption, path=path, validate_path_exists=False)
```

If the user-entered path does not exist, the interactive function should warn the user but still proceed.

### Decision 8: Manual end-to-end test

Status: Accepted with Option A.

Add a manual end-to-end script outside `tests/`:

```text
e2e/manual_prompt_for_report.py
```

It should call `prompt_for_report()` and display the returned Markdown. It is not part of the automated pytest suite.

## Proposed Architecture

The new interaction layer should sit above the existing generation and rendering APIs.

```text
prompt_for_report()
  |
  |-- prompt_toolkit prompts
  |     |-- ReportConfig fields
  |     |-- ChapterSpec fields
  |     |-- Plot/Table elements
  |
  |-- chapter_generators(config, specs, generation_order=...)
  |     |-- existing ChapterGenerator
  |     |-- existing ChapterDraft
  |
  |-- per-chapter draft loop
  |     |-- draft.current()
  |     |-- draft.revise(feedback)
  |     |-- draft.accept()
  |
  |-- order_sections(...)
  |
  |-- MarkdownRenderer().render(config, ordered_sections)
  |
  `-- return markdown string
```

The implementation should not move logic into `forelius/generator.py`. `prompt_toolkit` imports should stay localized to `forelius/interactive.py`.

## Data Flow

### 1. Prompt report config

Prompt required text fields:

- discipline;
- subject;
- language;
- figure label;
- table label.

Build:

```python
ReportConfig(
    discipline=...,
    subject=...,
    language=...,
    figure_label=...,
    table_label=...,
)
```

### 2. Prompt chapters

Loop until the user chooses not to add another chapter.

For each chapter:

- prompt chapter title;
- prompt/select chapter role from existing `ChapterRole` values:
  - introduction;
  - body;
  - conclusion;
- prompt pointers one by one until done;
- prompt elements one by one until done.

Build:

```python
ChapterSpec(
    role=role,
    title=title,
    pointers=pointers,
    elements=elements,
)
```

### 3. Prompt elements

For each element loop:

- ask for element type: `figure`, `table`, or `done`.

For figures:

- prompt caption;
- prompt path;
- if `Path(path).exists()` is false, display a warning to the user;
- construct:

```python
Plot(caption=caption, path=path, validate_path_exists=False)
```

For tables:

- prompt caption;
- prompt headers as a comma-separated list;
- prompt rows one by one as comma-separated lists;
- stop row entry when the user chooses done;
- construct:

```python
Table(caption=caption, headers=headers, rows=rows)
```

Use existing `Table` validation. If validation fails, show the validation error and re-prompt the table input.

### 4. Generate and revise each chapter

Use existing generators:

```python
generators = chapter_generators(config, specs, generation_order=GenerationOrder.REPORT)
```

For each generator:

```text
draft = generator.draft()
show draft.current().text
loop:
  action = accept / revise / abort
  if revise:
    feedback = prompt(...)
    section = draft.revise(feedback)
    show section.text
  if accept:
    accepted_sections.append(draft.accept())
    break
  if abort:
    raise InteractiveReportAborted
```

The first implementation should use `GenerationOrder.REPORT` unless the function later gains an optional parameter. This keeps the interactive flow minimal and avoids surprising users by generating chapters in a different order than entered.

### 5. Render final report

After all chapters are accepted:

```python
ordered_sections = order_sections(accepted_sections, GenerationOrder.REPORT)
markdown = MarkdownRenderer().render(config, ordered_sections)
```

Display drafts, warnings, validation messages, and the final Markdown using `prompt_toolkit.print_formatted_text()` where practical, then return the final Markdown string.

## API / Interface Changes

### New public function

In `forelius/interactive.py`:

```python
def prompt_for_report() -> str:
    """Interactively collect report inputs, generate/revise/accept chapters, and return Markdown."""
```

The function should be user-callable and should perform all prompting internally.

### Package root export

Update `forelius/__init__.py`:

```python
from forelius.interactive import InteractiveReportAborted, prompt_for_report
```

Add `"InteractiveReportAborted"` and `"prompt_for_report"` to `__all__`.

### Interactive abort exception

In `forelius/interactive.py`, define a custom exception:

```python
class InteractiveReportAborted(Exception):
    """Raised when the user aborts the interactive report flow."""
```

If the user chooses abort during chapter review, raise this exception. Do not silently return a partial report.

### Plot validation change

Update `forelius/elements.py` so `Plot` supports configurable path existence validation.

Current behavior:

```python
class Plot(BaseModel):
    caption: str
    path: Path

    @field_validator("path")
    @classmethod
    def validate_path_exists(cls, path: Path) -> Path:
        if not path.exists():
            raise ValueError("Plot path must exist")
        return path
```

Target behavior:

```python
class Plot(BaseModel):
    caption: str
    path: Path
    validate_path_exists: bool = True
```

Validation should check path existence only when `validate_path_exists` is true. Use a model-level validator if needed so the validator can see both `path` and `validate_path_exists`.

Strict validation should remain the default to minimize compatibility changes for existing direct API users. The interactive function and manual e2e flow should explicitly use `validate_path_exists=False` when creating figures.

### Prompt helper functions

`forelius/interactive.py` may define private helpers, for example:

```python
def _parse_csv_values(value: str) -> list[str]: ...
def _prompt_required_text(label: str) -> str: ...
def _prompt_choice(label: str, choices: list[str]) -> str: ...
def _prompt_yes_no(label: str, default: bool = False) -> bool: ...
def _prompt_elements() -> list[Plot | Table]: ...
def _prompt_table() -> Table: ...
def _prompt_figure() -> Plot: ...
```

These should remain internal unless a later design makes them public.

## Code Architecture Sketch

Before:

```text
forelius/
  __init__.py
  chapter.py
  config.py
  elements.py
  generator.py
  initialization.py
  section.py
  render/
    markdown.py

tests/
  test_exports.py
  test_models.py
  test_generator.py
  ...
```

After:

```text
forelius/
  __init__.py              # existing; export prompt_for_report
  chapter.py               # existing; unchanged
  config.py                # existing; unchanged
  elements.py              # existing; configurable Plot path validation
  generator.py             # existing; reused unchanged
  interactive.py           # new; prompt_toolkit-driven flow
  initialization.py        # existing; unchanged
  section.py               # existing; unchanged
  render/
    markdown.py            # existing; reused unchanged

tests/
  test_exports.py          # existing; add export assertion
  test_models.py           # existing; update/add Plot validation tests
  test_interactive.py      # new; helper/import tests
  ...

e2e/
  manual_prompt_for_report.py  # new; manual full interactive run
```

## File-by-File Implementation Plan

### `pyproject.toml`

- Existing file.
- Purpose: project metadata and dependencies.
- Required changes:
  - Add canonical package dependency `prompt-toolkit>=3` to `[project].dependencies`.
- Key dependencies:
  - Existing: `baml-py`, `pydantic`.
  - New: `prompt-toolkit>=3` package, imported in code as `prompt_toolkit`.
- Tests:
  - `uv run pytest` should still run without terminal input.

### `forelius/elements.py`

- Existing file.
- Purpose: element models and token registry.
- Required changes:
  - Add `validate_path_exists: bool = True` to `Plot`.
  - Replace or adjust the current path field validator so path existence is checked only when `validate_path_exists` is true.
  - Keep `path: Path`.
  - Leave `Table`, `ElementRegistry`, `ReportElement`, and token behavior unchanged.
- Key types/functions/classes:
  - `Plot`
  - `Table`
  - `ElementRegistry`
- Dependencies:
  - Existing Pydantic validation.
- Tests:
  - Existing strict missing-path behavior should still be tested with default `validate_path_exists=True`.
  - Add a test that missing paths are accepted with `validate_path_exists=False`.
  - Existing renderer and element tests should continue to pass.

### `forelius/interactive.py`

- New file.
- Purpose: simple prompt-toolkit interactive report function.
- Required changes:
  - Import `prompt_toolkit` primitives in this module only.
  - Use `prompt_toolkit.prompt()` for prompts and `prompt_toolkit.print_formatted_text()` for drafts, warnings, validation messages, and final output where practical.
  - Define `InteractiveReportAborted`.
  - Define `prompt_for_report() -> str`.
  - Prompt all report configuration fields.
  - Prompt chapters and roles.
  - Prompt pointers.
  - Prompt figure/table elements.
  - Warn when a figure path does not exist.
  - Construct interactive figures with `validate_path_exists=False`.
  - Generate chapters with existing `chapter_generators()`.
  - Use `ChapterDraft` revise/accept loop per chapter.
  - Render accepted sections with `MarkdownRenderer`.
  - Display final Markdown with `prompt_toolkit.print_formatted_text()` and return it.
  - Raise `InteractiveReportAborted` if the user aborts the flow.
- Key types/functions/classes:
  - `InteractiveReportAborted`
  - `prompt_for_report`
  - private helper functions for prompting, printing, and parsing as needed.
- Dependencies:
  - `prompt_toolkit`
  - `pathlib.Path`
  - `forelius.config.ReportConfig`
  - `forelius.chapter.ChapterRole`, `ChapterSpec`
  - `forelius.elements.Plot`, `Table`
  - `forelius.generator.GenerationOrder`, `chapter_generators`, `order_sections`
  - `forelius.render.markdown.MarkdownRenderer`
- Tests:
  - Import test.
  - Helper tests for CSV parsing and role/choice normalization if implemented.
  - Do not test full prompt loop with real terminal input.

### `forelius/__init__.py`

- Existing file.
- Purpose: public package exports.
- Required changes:
  - Import and export `InteractiveReportAborted` and `prompt_for_report`.
  - Add `"InteractiveReportAborted"` and `"prompt_for_report"` to `__all__`.
- Tests:
  - Update `tests/test_exports.py` to assert `forelius.prompt_for_report is not None` and `forelius.InteractiveReportAborted is not None`.
  - Ensure importing `forelius` still does not require API keys or terminal input.

### `tests/test_models.py`

- Existing file.
- Purpose: model behavior tests.
- Required changes:
  - Keep or update the existing missing-path test to assert strict default validation still rejects missing paths.
  - Add a new test showing missing paths are allowed with:

```python
Plot(caption="Draft figure", path=missing_path, validate_path_exists=False)
```

- Dependencies:
  - Existing pytest and Pydantic validation behavior.

### `tests/test_exports.py`

- Existing file.
- Purpose: package root export tests.
- Required changes:
  - Assert `forelius.prompt_for_report` is exported.
- Tests:
  - No live generation.
  - No terminal input.

### `tests/test_interactive.py`

- New file.
- Purpose: non-interactive tests for the new interactive module.
- Required changes:
  - Verify `forelius.interactive` imports.
  - Test pure helpers if they exist, especially comma-separated parsing.
- Suggested tests:
  - `_parse_csv_values("A, B, C") == ["A", "B", "C"]`.
  - `_parse_csv_values(" A ,, B ") == ["A", "B"]` if empty values are intentionally ignored.
  - Do not call `prompt_for_report()` unless prompt and generation dependencies are fully mocked.
- Dependencies:
  - pytest.

### `e2e/manual_prompt_for_report.py`

- New file.
- Purpose: manual full interactive end-to-end validation outside `tests/`.
- Required changes:
  - Import `prompt_for_report` from `forelius`.
  - Call it.
  - Print the returned Markdown.
  - Include a short module docstring or comments explaining:
    - this is manual;
    - it is intentionally outside `tests/`;
    - real generation may require `ANTHROPIC_API_KEY`.
- Key types/functions/classes:
  - `prompt_for_report`
- Dependencies:
  - package runtime dependencies, including `prompt_toolkit` and BAML runtime for real generation.
- Tests:
  - Not part of pytest.
- Manual command:

```bash
uv run python e2e/manual_prompt_for_report.py
```

## Testing Strategy

### Unit tests

Use existing pytest style.

Automated tests should cover:

- package export of `prompt_for_report`;
- import of `forelius.interactive`;
- pure helper parsing behavior if helpers are module-level and testable;
- configurable `Plot` validation:
  - strict default rejects missing paths;
  - `validate_path_exists=False` accepts missing paths.

Automated tests should not:

- require terminal input;
- call `prompt_for_report()` without extensive mocking;
- call live LLM/BAML generation;
- require `ANTHROPIC_API_KEY`.

### Integration tests

Existing offline integration tests remain unchanged.

No automated full interactive integration test is required in `tests/` for this change.

### Manual end-to-end test

Add manual script:

```text
e2e/manual_prompt_for_report.py
```

Run manually with:

```bash
uv run python e2e/manual_prompt_for_report.py
```

This full flow may make real BAML/LLM calls and may require:

```bash
export ANTHROPIC_API_KEY="..."
```

The interactive function should create figures with `validate_path_exists=False`, so manual runs can use placeholder figure paths. If a placeholder/missing path is entered, the user should see a warning but should be allowed to proceed.

### Validation commands

Automated validation:

```bash
uv run pytest
uv run baml-cli check
```

If BAML sources are not changed, `uv run baml-cli generate` is not required by this design, but remains the known regeneration command after BAML source changes:

```bash
uv run baml-cli generate
```

## Migration / Backward Compatibility

- Existing Python API remains intact.
- Existing generation and rendering APIs should not change.
- `Plot` gains a new optional field, `validate_path_exists`, with default `True` to preserve current strict behavior for direct API users.
- Interactive report creation explicitly passes `validate_path_exists=False` for figures.
- Existing tests that rely on strict default path validation can remain valid.
- New `prompt-toolkit>=3` dependency is a normal runtime dependency and is imported as `prompt_toolkit` in Python code.
- Importing `forelius` must still not require API keys or terminal interaction.

## Risks and Mitigations

### Risk: `prompt_toolkit` selection/confirmation helpers vary by version

- Why it matters: the user requested prompt/confirm/select-style primitives, but prompt-toolkit APIs differ between basic prompts and higher-level dialogs.
- Mitigation: use `prompt_toolkit.prompt()` plus simple validated loops for choices and confirmations if higher-level helpers are not suitable.

### Risk: Full interactive flow is not automated

- Why it matters: prompt sequencing bugs may not be caught by `pytest`.
- Mitigation: add `e2e/manual_prompt_for_report.py` for manual full-flow validation and keep helper logic small/testable.

### Risk: Missing figure paths produce broken Markdown images

- Why it matters: relaxed validation allows reports to refer to images that do not exist locally.
- Mitigation: preserve strict validation by default on `Plot`; interactive flow disables strict validation only deliberately and warns the user when a path is missing.

### Risk: Table entry via comma-separated prompts is limited

- Why it matters: cells containing commas are awkward.
- Mitigation: accept this as a minimal first implementation. Future interfaces can provide richer table editing.

### Risk: Abort behavior needs to be clear

- Why it matters: a user may choose abort after one or more generated chapters.
- Mitigation: define and raise `InteractiveReportAborted` from `forelius.interactive`. Avoid returning a partial report silently.

### Risk: Adding `prompt_for_report` to package root imports prompt-toolkit at package import time

- Why it matters: importing `forelius` should remain lightweight and should not require API keys or terminal interaction.
- Mitigation: `prompt_toolkit` is a normal dependency, so import availability is expected. The module must not prompt or initialize generation at import time.

## Validation Checklist

Implementation is complete when:

- [ ] `prompt-toolkit>=3` is listed in `pyproject.toml` dependencies.
- [ ] `forelius/interactive.py` exists.
- [ ] `prompt_for_report() -> str` exists.
- [ ] `prompt_for_report` uses `prompt_toolkit`, not primitive `input()`.
- [ ] `forelius.__init__` exports `prompt_for_report` and `InteractiveReportAborted`.
- [ ] Importing `forelius` does not prompt, initialize, or require API keys.
- [ ] `Plot` supports configurable `validate_path_exists` behavior.
- [ ] `Plot` remains strict by default.
- [ ] `Plot(..., validate_path_exists=False)` accepts missing paths.
- [ ] Interactive figure creation passes `validate_path_exists=False`.
- [ ] Interactive flow warns when a figure path does not exist.
- [ ] Interactive flow prompts for report config fields.
- [ ] Interactive flow prompts for chapters, roles, pointers, and elements.
- [ ] Interactive flow supports figure elements.
- [ ] Interactive flow supports table elements.
- [ ] Draft/revise/accept is a loop after generation.
- [ ] Accepted sections are rendered with `MarkdownRenderer`.
- [ ] Drafts, warnings, validation messages, and final Markdown use `prompt_toolkit.print_formatted_text()` where practical.
- [ ] Final Markdown is displayed and returned.
- [ ] User abort raises `InteractiveReportAborted` and does not return a partial report.
- [ ] No file writing is added.
- [ ] Automated tests do not require terminal input.
- [ ] Automated tests do not make live LLM calls.
- [ ] `e2e/manual_prompt_for_report.py` exists outside `tests/`.
- [ ] `uv run pytest` passes.
- [ ] `uv run baml-cli check` passes or is unaffected by this change.

## Open Questions

### Exact prompt-toolkit choice/confirm implementation

- Unknown: whether the implementation should use prompt-toolkit shortcut dialogs or basic prompts with validated loops.
- Why it matters: shortcut APIs may add complexity or version sensitivity.
- Conservative default: use `prompt_toolkit.prompt()` and implement simple validation loops for yes/no and choices.
- Status: Accepted with assumptions.

### Resolved implementation clarifications

The following previously open implementation choices are now fixed:

- Dependency specification: use `prompt-toolkit>=3` in `pyproject.toml` and import it as `prompt_toolkit` in Python code.
- Output primitive: use `prompt_toolkit.print_formatted_text()` for drafts, warnings, validation messages, and final Markdown where practical.
- Abort behavior: define and raise `InteractiveReportAborted` from `forelius.interactive`; do not return partial Markdown silently.

## Implementability Check

- Referenced existing files were verified during reconnaissance:
  - `pyproject.toml`
  - `forelius/__init__.py`
  - `forelius/elements.py`
  - `forelius/generator.py`
  - `forelius/chapter.py`
  - `forelius/config.py`
  - `forelius/render/markdown.py`
  - `tests/test_exports.py`
  - `tests/test_models.py`
- New files are explicitly marked as new:
  - `forelius/interactive.py`
  - `tests/test_interactive.py`
  - `e2e/manual_prompt_for_report.py`
- Proposed structure fits the existing repository layout:
  - new runtime code under `forelius/`;
  - automated tests under `tests/`;
  - manual e2e outside `tests/`.
- Dependency addition is justified:
  - `prompt-toolkit>=3` is required by the requested user interaction style and provides the `prompt_toolkit` import package.
- Existing architecture is preserved:
  - generation stays in `forelius/generator.py`;
  - rendering stays in `forelius/render/markdown.py`;
  - prompt interaction stays in `forelius/interactive.py`.
- Interface style matches the codebase:
  - existing Pydantic models are reused;
  - existing `ChapterDraft` is reused for revision;
  - existing `MarkdownRenderer` is reused for output.
- Tests match existing layout and philosophy:
  - pytest unit tests;
  - no live LLM calls;
  - no blocking terminal input.
- Validation commands are known from `README.md`:
  - `uv run pytest`;
  - `uv run baml-cli check`.
- No critical material decision is hidden:
  - public function boundary;
  - prompt flow;
  - element handling;
  - configurable path validation;
  - revise/accept loop;
  - output behavior;
  - dependency/testing approach;
  - manual e2e location.
- Coherent implementation order:
  1. Add `prompt-toolkit>=3` dependency.
  2. Add configurable `Plot` path validation and tests.
  3. Add `forelius/interactive.py` helpers and `prompt_for_report()`.
  4. Export `prompt_for_report`.
  5. Add import/helper tests.
  6. Add manual e2e script.
  7. Run automated validation.
