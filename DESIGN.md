# Design: Safe LLM-Assisted Plot Generation

## Summary

Add safe plot generation to Forelius. Users provide freeform data plus a natural-language plot request. Forelius uses BAML/LLM calls only for structured data extraction and constrained plot intent creation/revision. Forelius never executes LLM-generated code. It validates and normalizes extracted data, renders trusted matplotlib PNG output, and returns the existing `forelius.elements.Plot` so generated plots work with the current report pipeline.

V1 includes a reusable Python service/session API with revision support. V1 does not add generated plots to the existing interactive CLI menu.

## Goals

- Accept messy/freeform user input containing data and plot instructions.
- Number input lines before extraction so extracted data is auditable.
- Use BAML to extract a column-oriented dataset.
- Validate LLM output strictly before rendering.
- Normalize numeric values once into a validated dataset.
- Normalize common missing/deviant/non-finite numeric tokens to `float("nan")` so matplotlib ignores those points or breaks line segments naturally.
- Use BAML to create and revise constrained XY plot intents.
- Render PNG plots using trusted internal matplotlib code with the `Agg` backend.
- Return/hold normal `Plot` objects that integrate with existing report elements.
- Support a revision loop through a service/session API:
  - user feedback;
  - revised intent;
  - new rendered plot;
  - repeat until accepted by the caller.
- Keep automated tests offline by mocking BAML calls.

## Non-Goals

- No LLM-generated Python or arbitrary matplotlib code execution.
- No interactive CLI `"grafiek"` menu integration in v1.
- No automatic OS image viewer opening in v1.
- No bar charts, grouped plots, multiple subplots, or multi-series plot types in v1.
- No SVG/PDF export in v1.
- No pandas dependency for v1 numeric parsing.
- No change to existing `Plot`, `Table`, `ChapterSpec`, `ElementRegistry`, or `MarkdownRenderer` behavior unless required by tests.

## Existing Codebase Context

- `forelius/elements.py` already defines:
  - `Plot(caption: str, path: Path, validate_path_exists: bool = True)`;
  - `Table`;
  - `ElementRegistry`, which registers `Plot` objects as figures with IDs like `fig_0001`.
- `forelius/render/markdown.py` already renders `Plot` as Markdown image syntax and visible figure captions.
- `forelius/chapter.py` already supports `elements: list[Plot | Table]`.
- `forelius/generator.py` already demonstrates BAML dispatch through `baml_client.sync_client.b` and generated `baml_client.types`.
- BAML source is currently organized under `baml_src/report/`; plotting should use a parallel `baml_src/plotting/` module.
- `baml_client/` is checked in and must be regenerated after BAML source changes.
- Runtime dependencies currently do not include matplotlib.
- Tests are under `tests/`; normal tests should not make live LLM calls.
- README documents validation commands:
  - `uv run baml-cli check`
  - `uv run baml-cli generate`
  - `uv run pytest`

## Relevant Files and Modules

Existing files likely changed by implementation:

- `pyproject.toml` — add required `matplotlib` runtime dependency.
- `uv.lock` — regenerated after dependency changes.
- `forelius/__init__.py` — export `generate_plot_from_freeform` from the root package API.
- `baml_client/...` — regenerated after adding plotting BAML.
- `tests/test_baml_contracts.py` — add plotting BAML source contract tests, or split into a new plotting BAML contract test file.
- `tests/test_exports.py` — update to assert root-level `generate_plot_from_freeform` export.
- `README.md` — optional documentation for plotting API and manual usage.

New files likely added:

- `forelius/plotting/__init__.py`
- `forelius/plotting/errors.py`
- `forelius/plotting/data.py`
- `forelius/plotting/intent.py`
- `forelius/plotting/render.py`
- `forelius/plotting/service.py`
- `baml_src/plotting/shared.baml`
- `baml_src/plotting/extraction.baml`
- `baml_src/plotting/intent.baml`
- `baml_src/plotting/revision.baml`
- `tests/test_plotting_data.py`
- `tests/test_plotting_intent.py`
- `tests/test_plotting_render.py`
- `tests/test_plotting_service.py`
- `e2e/manual_generate_plot.py` — optional manual live-LLM script.

## Accepted Design Decisions

1. **Package boundaries:** create `forelius/plotting/` with data, intent, rendering, errors, and service/session modules; export `generate_plot_from_freeform` from root `forelius.__init__`.
2. **Rendering dependency:** add `matplotlib` as a required runtime dependency; use `Agg`; render PNG only in v1.
3. **Dataset model:** use column-oriented `ExtractedDataset` preserving raw string values from BAML.
4. **Numeric normalization:** create a `ValidatedDataset`; parse once; normalize common missing/deviant/non-finite tokens to `float("nan")`.
5. **Plot intent:** BAML creates full constrained `XYPlotIntent`; Forelius validates strictly before rendering.
6. **Low confidence:** reject `confidence == "low"` before rendering.
7. **Output policy:** require explicit `output_dir`; create it if needed; write safe, non-overwriting PNG filenames.
8. **BAML organization:** add plotting BAML under `baml_src/plotting/`; regenerate checked-in `baml_client/`.
9. **Revision loop:** include `ReviseXYPlotIntent` and a service/session revision flow in v1.
10. **Interactive CLI:** do not add generated-plot prompts to `forelius/interactive.py` in v1.
11. **Testing:** use layered offline tests plus optional manual/e2e script.

## Proposed Architecture

Add a plotting package that is independent of report generation and integrates through the existing `Plot` model.

```text
forelius/
  elements.py                 # existing Plot remains the integration point
  plotting/
    __init__.py               # selected exports
    errors.py                 # plotting-specific exceptions
    data.py                   # extracted/validated dataset models and numeric normalization
    intent.py                 # XY plot intent models and validators
    render.py                 # trusted matplotlib renderer
    service.py                # BAML orchestration and revision session
```

BAML organization:

```text
baml_src/
  clients.baml                # existing client config
  report/                     # existing report generation BAML
  plotting/
    shared.baml               # plotting schemas
    extraction.baml           # ExtractDatasetFromFreeform
    intent.baml               # CreateXYPlotIntent
    revision.baml             # ReviseXYPlotIntent
```

V1 service/session interface:

```python
class PlotGenerationSession(BaseModel):
    dataset: ValidatedDataset
    intent: XYPlotIntent
    plot: Plot
    output_dir: Path

    def revise(self, feedback: str, filename_stem: str | None = None) -> "PlotGenerationSession": ...


def generate_plot_session(
    request: str,
    output_dir: Path,
    filename_stem: str | None = None,
) -> PlotGenerationSession: ...
```

Root-exported convenience function:

```python
def generate_plot_from_freeform(
    request: str,
    output_dir: Path,
    filename_stem: str | None = None,
) -> Plot:
    return generate_plot_session(request, output_dir, filename_stem).plot
```

Export `generate_plot_from_freeform` from the root `forelius.__init__` API in v1. Keep session-oriented APIs such as `generate_plot_session` and `PlotGenerationSession` available from `forelius.plotting`, not from the root package.

Expected revision-loop usage by callers:

```python
session = generate_plot_session(request, output_dir)
# show or print session.plot.path
session = session.revise("Maak er alleen punten van.")
# show or print session.plot.path again
final_plot = session.plot
```

The service/session API performs one generation or one revision per call. It does not prompt users directly; caller code owns accept/revise/abort looping.

## Data Flow

Initial generation:

```text
freeform request/data
  ↓
number_input_lines(...)
  ↓
BAML ExtractDatasetFromFreeform(numbered_input)
  ↓
ExtractedDataset
  ↓
reject if confidence == "low"
  ↓
validate_extracted_dataset(...)
  ↓
ValidatedDataset with normalized numeric values
  ↓
BAML CreateXYPlotIntent(request + sanitized dataset metadata/preview)
  ↓
XYPlotIntent
  ↓
validate_plot_intent(intent, validated_dataset)
  ↓
render_xy_plot(validated_dataset, intent, output_dir, filename_stem)
  ↓
PlotGenerationSession(plot=Plot(...), dataset=..., intent=...)
```

Revision:

```text
current PlotGenerationSession + user feedback
  ↓
BAML ReviseXYPlotIntent(current_intent, sanitized dataset metadata/preview, feedback)
  ↓
revised XYPlotIntent
  ↓
validate_plot_intent(revised_intent, same validated_dataset)
  ↓
render_xy_plot(...)
  ↓
new PlotGenerationSession with same dataset and new intent/plot
```

NaN handling:

```text
"4,1"       -> 4.1
"-"         -> float("nan")
"n/a"       -> float("nan")
"NaN"       -> float("nan")
"Infinity"  -> float("nan")
"-inf"      -> float("nan")
```

Matplotlib receives NaN values so points are ignored and line segments break naturally. Intent validation must still require at least two finite x/y pairs for the selected columns.

BAML intent/revision functions must not receive full numeric arrays and must not receive serialized Python `float("nan")` values. `CreateXYPlotIntent` and `ReviseXYPlotIntent` need column-selection context, not plotting arrays. Send only sanitized dataset metadata/previews, such as:

```text
- column name
- unit
- data_type
- value_count
- finite_count for numeric columns
- ignored_count for numeric columns
- first few raw source values as strings, if useful
```

This avoids non-standard JSON/BAML serialization of NaN while preserving NaN as the internal renderer representation.

## API / Interface Changes

### New plotting errors

```python
class PlottingError(ValueError): ...
class PlotDataError(PlottingError): ...
class PlotIntentError(PlottingError): ...
class PlotRenderingError(PlottingError): ...
```

### New data models

```python
class ExtractedColumn(BaseModel):
    name: str
    unit: str | None = None
    data_type: Literal["number", "text", "category", "date"]
    values: list[str]

class ExtractedDataset(BaseModel):
    data_start_line: int
    data_end_line: int
    columns: list[ExtractedColumn]
    confidence: Literal["low", "medium", "high"]
    assumptions: list[str] = Field(default_factory=list)

class ValidatedColumn(BaseModel):
    name: str
    unit: str | None = None
    data_type: Literal["number", "text", "category", "date"]
    values: list[str]
    numeric_values: list[float] | None = None

class ValidatedDataset(BaseModel):
    source: ExtractedDataset
    columns: list[ValidatedColumn]
    assumptions: list[str] = Field(default_factory=list)

class DatasetColumnMetadata(BaseModel):
    name: str
    unit: str | None = None
    data_type: Literal["number", "text", "category", "date"]
    value_count: int
    finite_count: int | None = None
    ignored_count: int | None = None
    sample_values: list[str] = Field(default_factory=list)

class DatasetMetadata(BaseModel):
    columns: list[DatasetColumnMetadata]
    assumptions: list[str] = Field(default_factory=list)
```

For numeric columns, `numeric_values` contains floats and may include `float("nan")`. `DatasetMetadata` is the JSON-safe summary passed to BAML intent/revision functions; it must not include raw `float("nan")` values.

### New data helpers

```python
number_input_lines(text: str) -> str
validate_extracted_dataset(dataset: ExtractedDataset) -> ValidatedDataset
parse_numeric_value(value: str) -> float
count_finite_pairs(x_values: list[float], y_values: list[float]) -> int
build_dataset_metadata(dataset: ValidatedDataset) -> DatasetMetadata
```

Numeric parser supports at least:

```text
4.1
4,1
1,234.56
1.234,56
1000
-12,5
+12.5
```

Use a conservative separator heuristic:

- If both `.` and `,` occur, the rightmost separator is decimal; the other is thousands.
- If only one separator occurs, treat it as decimal unless it clearly matches repeated thousands grouping.
- Strip surrounding whitespace.
- Do not accept arbitrary unit suffixes in numeric values for v1.
- Common missing/deviant/non-finite tokens normalize to `float("nan")`.

Recommended missing/deviant/non-finite tokens include case-insensitive:

```text
"", "-", "—", "n/a", "na", "null", "none", "geen",
"nan", "+nan", "-nan", "inf", "+inf", "-inf",
"infinity", "+infinity", "-infinity"
```

### New intent models

```python
class XYPlotOptions(BaseModel):
    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    x_lim: tuple[float, float] | None = None
    y_lim: tuple[float, float] | None = None
    grid: Literal["none", "major", "both"] = "major"
    line_style: Literal["solid", "dashed", "dotted", "dashdot", "none"] = "solid"
    marker: Literal["none", "circle", "square", "triangle", "diamond", "cross"] = "none"
    color: str | None = None
    invert_x: bool = False
    invert_y: bool = False

class XYPlotIntent(BaseModel):
    x: str
    y: str
    caption: str
    options: XYPlotOptions = Field(default_factory=XYPlotOptions)
```

Validation rules:

- `x` and `y` columns exist.
- `x` and `y` columns are numeric.
- selected x/y columns have equal lengths.
- selected x/y columns have at least two finite pairs after normalization.
- `line_style` and `marker` are not both `"none"`.
- axis limits are increasing when present.
- text fields have bounded lengths: `title`, `x_label`, and `y_label` max 120 characters each; `caption` max 300 characters.
- color is optional; if omitted, do not pass `color` so matplotlib uses its default color cycle; if provided by the user/intent, validate with `matplotlib.colors.is_color_like` before rendering.

BAML must declare all finite categorical plot options as enums, not unconstrained strings. Required BAML enum concepts:

```text
PlotGrid: NONE, MAJOR, BOTH
PlotLineStyle: SOLID, DASHED, DOTTED, DASHDOT, NONE
PlotMarker: NONE, CIRCLE, SQUARE, TRIANGLE, DIAMOND, CROSS
```

The service layer maps BAML enum values to the Python literal strings used by `XYPlotOptions`, for example `PlotGrid.MAJOR -> "major"`. Freeform/scalar plot fields are not enums: `title`, `x_label`, `y_label`, axis limits, booleans, and `color`. `color` remains `str | None` because user-requested matplotlib-compatible colors are intentionally allowed and then validated in Python.

### Rendering interface

```python
def render_xy_plot(
    dataset: ValidatedDataset,
    intent: XYPlotIntent,
    output_dir: Path,
    filename_stem: str | None = None,
) -> Plot: ...
```

Renderer requirements:

- Configure `matplotlib.use("Agg")` before importing `matplotlib.pyplot`.
- Save PNG only in v1.
- Create `output_dir` with `parents=True, exist_ok=True`.
- Generate safe non-overwriting filenames.
- Never use raw LLM text directly as a filename.
- Use `ax.plot(...)` with constrained line/marker mappings.
- If `intent.options.color is None`, do not pass a color argument so matplotlib uses its default color cycle.
- If `intent.options.color` is set, validate it with `matplotlib.colors.is_color_like` and pass it through to matplotlib.
- Apply title, labels, limits, grid, and axis inversion.
- Save image.
- Close figures after saving.
- Return `Plot(caption=intent.caption, path=output_path)`.

Line and marker mappings:

```python
LINESTYLE_MAP = {
    "solid": "-",
    "dashed": "--",
    "dotted": ":",
    "dashdot": "-.",
    "none": "",
}

MARKER_MAP = {
    "none": "",
    "circle": "o",
    "square": "s",
    "triangle": "^",
    "diamond": "D",
    "cross": "x",
}
```

## Code Architecture Sketch

Before:

```text
forelius/
  elements.py          # Plot, Table
  generator.py         # report chapter BAML dispatch
  interactive.py       # manual figure/table prompts
  render/markdown.py   # renders Plot as image
baml_src/
  report/              # report BAML only
```

After:

```text
forelius/
  elements.py          # unchanged integration point
  plotting/
    errors.py          # new error hierarchy
    data.py            # raw + validated datasets
    intent.py          # constrained XY intent
    render.py          # trusted PNG renderer
    service.py         # BAML orchestration + session revisions
  render/markdown.py   # unchanged; already renders Plot
baml_src/
  report/              # unchanged report prompts
  plotting/            # new extraction/intent/revision prompts
```

## File-by-File Implementation Plan

### `forelius/plotting/errors.py`

- New file.
- Purpose: plotting-specific exception hierarchy.
- Required changes:
  - define `PlottingError`, `PlotDataError`, `PlotIntentError`, `PlotRenderingError`.
- Key types/functions/classes:
  - error classes only.
- Dependencies:
  - standard Python only.
- Tests:
  - indirect through data/intent/service tests; optional direct subclass assertions.

### `forelius/plotting/data.py`

- New file.
- Purpose: extracted dataset models, validation, numeric normalization.
- Required changes:
  - define `ExtractedColumn`, `ExtractedDataset`, `ValidatedColumn`, `ValidatedDataset`, `DatasetColumnMetadata`, and `DatasetMetadata`;
  - implement `number_input_lines`;
  - implement numeric parser and missing/deviant token normalization to `float("nan")`;
  - implement `validate_extracted_dataset`;
  - implement `build_dataset_metadata` to create JSON-safe BAML intent/revision inputs;
  - normalize duplicate column names deterministically, e.g. `"Value"`, `"Value_2"`.
- Key types/functions/classes:
  - `ExtractedColumn`, `ExtractedDataset`, `ValidatedColumn`, `ValidatedDataset`, `DatasetColumnMetadata`, `DatasetMetadata`;
  - `number_input_lines`, `parse_numeric_value`, `validate_extracted_dataset`, `count_finite_pairs`, `build_dataset_metadata`.
- Dependencies:
  - `pydantic`, `math`, `re`, typing literals.
- Tests:
  - `tests/test_plotting_data.py`.

### `forelius/plotting/intent.py`

- New file.
- Purpose: constrained XY plot intent and validation.
- Required changes:
  - define `XYPlotOptions`, `XYPlotIntent`;
  - implement `validate_plot_intent(intent, dataset)`.
- Key types/functions/classes:
  - `XYPlotOptions`, `XYPlotIntent`, `validate_plot_intent`.
- Dependencies:
  - `pydantic`, `forelius.plotting.data`, `forelius.plotting.errors`.
- Tests:
  - `tests/test_plotting_intent.py`.

### `forelius/plotting/render.py`

- New file.
- Purpose: trusted matplotlib rendering to PNG.
- Required changes:
  - configure `Agg` backend before importing `pyplot`;
  - define line/marker maps;
  - implement safe filename generation/sanitization;
  - implement `render_xy_plot`.
- Key types/functions/classes:
  - `render_xy_plot`;
  - internal filename helpers.
- Dependencies:
  - `matplotlib`, `pathlib`, `uuid` or equivalent, `forelius.elements.Plot`, plotting data/intent modules.
- Tests:
  - `tests/test_plotting_render.py`.

### `forelius/plotting/service.py`

- New file.
- Purpose: orchestrate BAML extraction, validation, intent creation, rendering, and revisions.
- Required changes:
  - implement BAML dispatch for extraction, initial intent, and revision;
  - convert generated BAML types to Python Pydantic plotting models;
  - build sanitized `DatasetMetadata` from `ValidatedDataset` for intent/revision calls, excluding full numeric arrays and excluding Python NaN values;
  - implement `generate_plot_session`;
  - implement `PlotGenerationSession.revise(...)`;
  - implement root-exported convenience `generate_plot_from_freeform` returning `Plot`.
- Key types/functions/classes:
  - `PlotGenerationSession`;
  - `generate_plot_session`;
  - `generate_plot_from_freeform`.
- Dependencies:
  - `baml_client.sync_client.b`, `baml_client.types`, `ensure_initialized`, plotting modules.
- Tests:
  - `tests/test_plotting_service.py` with mocked BAML calls.

### `forelius/plotting/__init__.py`

- New file.
- Purpose: package-level exports.
- Required changes:
  - export stable plotting models/errors/service functions.
  - avoid exporting internal filename helpers.
- Key types/functions/classes:
  - `generate_plot_session`, `generate_plot_from_freeform`, `PlotGenerationSession`, key errors and models.
- Dependencies:
  - local plotting modules.
- Tests:
  - import tests in `tests/test_exports.py` or plotting-specific tests.

### `pyproject.toml`

- Existing file.
- Purpose: runtime dependencies.
- Required changes:
  - add `matplotlib` to `[project].dependencies`.
- Key types/functions/classes:
  - Not applicable.
- Dependencies:
  - add dependency compatible with Python `>=3.12`.
- Tests:
  - renderer tests depend on matplotlib being installed.

### `uv.lock`

- Existing generated lock file.
- Purpose: dependency lock.
- Required changes:
  - regenerate after adding matplotlib.
- Key types/functions/classes:
  - Not applicable.
- Dependencies:
  - generated from dependency resolver.
- Tests:
  - `uv run pytest` should use locked dependencies.

### `baml_src/plotting/shared.baml`

- New file.
- Purpose: BAML classes/input schemas for plotting.
- Required changes:
  - define BAML equivalents for raw extraction output: `ExtractedColumn` and `ExtractedDataset`;
  - define sanitized metadata input classes for intent/revision, not full numeric arrays;
  - define BAML equivalents for `XYPlotOptions` and `XYPlotIntent`;
  - mirror Python field names exactly where practical;
  - declare BAML enums for all finite categorical fields, including confidence, data type, grid, line style, and marker;
  - do not model finite categorical plot options as unconstrained BAML strings;
  - map generated BAML enum values to Python `Literal` string values in the service layer.
- Key types/functions/classes:
  - `ExtractionConfidence`, `ExtractedDataType`, `PlotGrid`, `PlotLineStyle`, `PlotMarker`, `ExtractedColumn`, `ExtractedDataset`, `DatasetColumnMetadata`, `DatasetMetadata`, `XYPlotOptions`, `XYPlotIntent`, `CreateXYPlotIntentInput`, `ReviseXYPlotIntentInput`.
- Sanitized metadata must include only JSON-safe values, for example:
  - `name string`;
  - `unit string?`;
  - `data_type`;
  - `value_count int`;
  - `finite_count int?`;
  - `ignored_count int?`;
  - `sample_values string[]`.
- Dependencies:
  - BAML only; uses existing client from `baml_src/clients.baml`.
- Tests:
  - BAML contract tests.

### `baml_src/plotting/extraction.baml`

- New file.
- Purpose: extract structured dataset from numbered freeform input.
- Required changes:
  - define `ExtractDatasetFromFreeform(numbered_input: string) -> ExtractedDataset`;
  - prompt must require:
    - return only explicitly present data;
    - do not invent rows/values;
    - preserve original value strings;
    - include line range;
    - use column-oriented output;
    - do not generate code.
- Key types/functions/classes:
  - `ExtractDatasetFromFreeform`.
- Dependencies:
  - `ForeliusClaudeHaiku45` client.
- Tests:
  - BAML contract tests; optional BAML native tests.

### `baml_src/plotting/intent.baml`

- New file.
- Purpose: create initial constrained XY plot intent.
- Required changes:
  - define `CreateXYPlotIntent(input: CreateXYPlotIntentInput) -> XYPlotIntent`;
  - input includes the original user request plus sanitized `DatasetMetadata` only;
  - do not pass full parsed numeric arrays or Python NaN values to BAML;
  - prompt must constrain output to existing columns and supported options.
- Key types/functions/classes:
  - `CreateXYPlotIntent`.
- Dependencies:
  - `ForeliusClaudeHaiku45` client.
- Tests:
  - BAML contract tests; optional BAML native tests.

### `baml_src/plotting/revision.baml`

- New file.
- Purpose: revise plot intent from user feedback while preserving dataset.
- Required changes:
  - define `ReviseXYPlotIntent(input: ReviseXYPlotIntentInput) -> XYPlotIntent`;
  - input includes current intent, user feedback, and sanitized `DatasetMetadata` only;
  - do not pass full parsed numeric arrays or Python NaN values to BAML;
  - prompt must preserve unspecified settings;
  - prompt must not invent columns;
  - prompt must only revise intent, not data.
- Key types/functions/classes:
  - `ReviseXYPlotIntent`.
- Dependencies:
  - `ForeliusClaudeHaiku45` client.
- Tests:
  - BAML contract tests; service revision tests with mocked BAML.

### `baml_client/...`

- Existing generated files.
- Purpose: generated Python client/types for BAML.
- Required changes:
  - regenerate after adding plotting BAML:
    - `uv run baml-cli generate`.
- Key types/functions/classes:
  - generated plotting types and client methods.
- Dependencies:
  - BAML generator.
- Tests:
  - service tests import generated types/client symbols; `uv run baml-cli check`.

### `forelius/__init__.py`

- Existing file.
- Purpose: root public API exports.
- Required changes:
  - import and export `generate_plot_from_freeform`;
  - add `"generate_plot_from_freeform"` to `__all__`;
  - do not export `generate_plot_session` or `PlotGenerationSession` from the root package in v1.
- Key types/functions/classes:
  - `generate_plot_from_freeform`;
  - `__all__` entry.
- Dependencies:
  - `forelius.plotting`.
- Tests:
  - update `tests/test_exports.py` to assert `forelius.generate_plot_from_freeform is not None`.

### `tests/test_plotting_data.py`

- New file.
- Purpose: unit tests for data models, validation, and numeric normalization.
- Required changes:
  - test line numbering;
  - valid dataset validation;
  - invalid line ranges;
  - fewer than two columns;
  - empty/duplicate column names;
  - unequal column lengths;
  - fewer than two values;
  - numeric parser formats;
  - missing/deviant/non-finite tokens become NaN.
- Key types/functions/classes:
  - tests for `forelius.plotting.data`.
- Dependencies:
  - pytest, math.
- Tests:
  - Not applicable; this is a test file.

### `tests/test_plotting_intent.py`

- New file.
- Purpose: unit tests for intent validation.
- Required changes:
  - reject missing x/y columns;
  - reject non-numeric x/y;
  - reject fewer than two finite pairs;
  - reject invisible plot style;
  - reject invalid limits;
  - accept valid intent.
- Key types/functions/classes:
  - tests for `forelius.plotting.intent`.
- Dependencies:
  - pytest.
- Tests:
  - Not applicable.

### `tests/test_plotting_render.py`

- New file.
- Purpose: offline renderer tests.
- Required changes:
  - render PNG to `tmp_path`;
  - verify output exists;
  - verify returned object is `Plot`;
  - verify `.png` suffix;
  - verify output directory creation;
  - verify safe filenames and non-overwrite behavior;
  - verify figures are closed after rendering.
- Key types/functions/classes:
  - tests for `render_xy_plot`.
- Dependencies:
  - pytest, matplotlib.
- Tests:
  - Not applicable.

### `tests/test_plotting_service.py`

- New file.
- Purpose: service/session tests with mocked BAML.
- Required changes:
  - initial generation calls extraction, validation, intent creation, rendering;
  - low confidence prevents intent creation and rendering;
  - invalid dataset/intent errors prevent rendering;
  - revision reuses the same validated dataset;
  - revision preserves unspecified settings through BAML prompt contract/mocked response expectations;
  - revision renders a new PNG/session.
- Key types/functions/classes:
  - tests for `generate_plot_session`, `PlotGenerationSession.revise`.
- Dependencies:
  - pytest, monkeypatch/unittest.mock, tmp_path.
- Tests:
  - Not applicable.

### `tests/test_baml_contracts.py` or new plotting BAML contract test

- Existing file or new test file.
- Purpose: source-level BAML contract tests.
- Required changes:
  - assert plotting BAML files exist;
  - assert functions exist:
    - `ExtractDatasetFromFreeform`;
    - `CreateXYPlotIntent`;
    - `ReviseXYPlotIntent`;
  - assert functions use `client ForeliusClaudeHaiku45`;
  - assert extraction prompt includes safety constraints such as do not invent data and do not generate code.
- Key types/functions/classes:
  - source text assertions.
- Dependencies:
  - pathlib.
- Tests:
  - Not applicable.

### `e2e/manual_generate_plot.py`

- Optional new file.
- Purpose: manual live-LLM plot generation/revision test.
- Required changes:
  - call `initialize()`;
  - call `generate_plot_session` with example Dutch data;
  - print saved plot path;
  - optionally ask for revision feedback in a simple loop.
- Key types/functions/classes:
  - manual script only.
- Dependencies:
  - real `ANTHROPIC_API_KEY`.
- Tests:
  - not part of automated tests.

## Testing Strategy

### Unit tests

Add:

- `tests/test_plotting_data.py`
- `tests/test_plotting_intent.py`

Cover:

- line numbering;
- dataset validation;
- duplicate column normalization;
- numeric parsing;
- missing/deviant/non-finite token normalization to NaN;
- finite-pair counting;
- intent validation.

### Renderer tests

Add `tests/test_plotting_render.py`.

Cover:

- PNG file is written to `tmp_path`;
- `Plot` path exists and validates;
- `Agg` backend is used safely;
- figure objects are closed after saving;
- NaN values are accepted by renderer;
- safe filename behavior.

### Service/session tests

Add `tests/test_plotting_service.py`.

Mock generated BAML calls from `baml_client.sync_client.b`.

Cover:

- successful initial generation;
- low-confidence extraction rejection;
- invalid dataset/intent rejection;
- revision flow calls `ReviseXYPlotIntent`;
- intent/revision BAML calls receive sanitized `DatasetMetadata`, not full numeric arrays or NaN floats;
- revision reuses dataset;
- revision creates a new rendered plot/session;
- automated tests do not call live LLMs.

### BAML contract tests

Extend `tests/test_baml_contracts.py` or add a plotting-specific contract test file.

Cover:

- plotting BAML files and functions exist;
- plotting BAML declares enum types for confidence, data type, grid, line style, and marker;
- plotting functions use `ForeliusClaudeHaiku45`;
- prompts include safety constraints;
- representative BAML native tests/fixtures may be added following existing report patterns.

### Regression tests

Add regressions for:

- Dutch decimal commas;
- mixed thousands/decimal separators;
- `NaN`/`Infinity` normalization to ignored plot values;
- fewer than two finite x/y pairs fails validation;
- existing `Plot`/Markdown rendering remains unchanged.

### Fixtures

If BAML fixtures are added, place them under existing `tests/fixtures/baml/` using a plotting-specific naming convention, for example:

```text
tests/fixtures/baml/extract_dataset_*.json
tests/fixtures/baml/create_xy_plot_intent_*.json
tests/fixtures/baml/revise_xy_plot_intent_*.json
```

### Validation commands

Run:

```bash
uv run baml-cli check
uv run baml-cli generate
uv run pytest
```

Recommended implementation order:

1. Add matplotlib dependency and regenerate lock.
2. Add plotting data/intent/render modules and unit tests.
3. Add BAML source.
4. Run `uv run baml-cli check`.
5. Run `uv run baml-cli generate`.
6. Add service/session layer and mocked BAML tests.
7. Run `uv run pytest`.

## Migration / Backward Compatibility

- Existing `Plot` behavior remains unchanged.
- Existing report generation APIs remain unchanged.
- Existing interactive CLI behavior remains unchanged in v1.
- Existing Markdown rendering remains unchanged because generated plots are normal `Plot` objects.
- Adding matplotlib increases runtime dependencies but does not affect existing public model shapes.
- BAML client regeneration updates checked-in generated files but should preserve existing report functions.

## Risks and Mitigations

### Risk: LLM extracts incorrect data

Mitigation:

- line numbering;
- strict dataset validation;
- reject low confidence;
- preserve assumptions;
- do not invent data prompt constraints.

### Risk: LLM chooses invalid plot intent

Mitigation:

- constrained `XYPlotIntent` model;
- strict intent validation;
- no arbitrary matplotlib kwargs;
- no LLM-generated code.

### Risk: Ambiguous numeric formats

Mitigation:

- deterministic parser;
- conservative separator heuristic;
- focused parser tests;
- preserve raw values in `ExtractedDataset`.

### Risk: NaN handling hides too much data

Mitigation:

- normalize only known missing/deviant/non-finite tokens;
- require at least two finite x/y pairs;
- keep raw values available in `ValidatedDataset.source`.

### Risk: NaN serialization across BAML/JSON boundaries

Mitigation:

- keep `float("nan")` only inside `ValidatedDataset.numeric_values` for renderer use;
- never pass full numeric arrays to BAML intent/revision functions;
- pass only JSON-safe `DatasetMetadata` with counts and raw string samples.

### Risk: Matplotlib backend issues in CI/headless environments

Mitigation:

- configure `Agg` before importing `pyplot`;
- renderer tests in normal pytest suite.

### Risk: Generated file collisions or unsafe filenames

Mitigation:

- require explicit `output_dir`;
- sanitize provided filename stems;
- generate UUID-based fallback filenames;
- avoid overwriting existing files.

### Risk: BAML/Python schema drift

Mitigation:

- source contract tests;
- service tests using generated types/client symbols;
- BAML contract tests asserting finite plot options are enums, not unconstrained strings;
- require `uv run baml-cli check` and `uv run baml-cli generate`.

### Risk: Revision API needs future UI changes

Mitigation:

- keep revision in reusable service/session layer;
- defer interactive CLI integration;
- final accepted value remains a normal `Plot`.

## Validation Checklist

Implementability checks:

- [ ] Existing referenced files exist:
  - `forelius/elements.py`
  - `forelius/render/markdown.py`
  - `forelius/generator.py`
  - `forelius/interactive.py`
  - `baml_src/clients.baml`
  - `tests/test_baml_contracts.py`
- [ ] New files are created under existing package/test layout.
- [ ] `forelius/plotting/` fits the current module organization.
- [ ] `matplotlib` is added to runtime dependencies before renderer tests are expected to pass.
- [ ] `Agg` backend is configured before `pyplot` import.
- [ ] Generated plots return existing `Plot` objects.
- [ ] `generate_plot_from_freeform` is exported from root `forelius.__init__` and covered by `tests/test_exports.py`.
- [ ] BAML intent/revision inputs use sanitized `DatasetMetadata` and do not serialize Python NaN values.
- [ ] BAML schemas declare enums for finite categorical plot options: grid, line style, and marker.
- [ ] Existing report rendering does not need changes.
- [ ] BAML source lives under `baml_src/plotting/`, separate from report BAML.
- [ ] `baml_client/` is regenerated after BAML edits.
- [ ] Automated tests mock BAML and do not call live LLMs.
- [ ] Test locations match existing `tests/test_*.py` layout.
- [ ] Validation commands are run:
  - `uv run baml-cli check`
  - `uv run baml-cli generate`
  - `uv run pytest`
- [ ] No hidden critical decisions remain for v1 implementation.
- [ ] Implementation order is coherent: models/renderer first, then BAML, then service/session.

## Open Questions

No blocking open questions for v1.

Accepted assumptions to preserve during implementation:

- Preview/display means returning or printing the saved PNG path; automatic image opening is not part of v1.
- Root `forelius.__init__` exports `generate_plot_from_freeform`; update `tests/test_exports.py` accordingly.
- Manual live-LLM script is optional and should not be part of automated validation.
