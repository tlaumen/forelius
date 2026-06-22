# Design: Forelius MVP Documentation Library

## Summary

Forelius is an MVP Python package for generating civil-engineering report chapters with BAML-backed LLM prompts, deterministic figure/table placeholder handling, interactive revision, and simple Markdown rendering.

The MVP will implement:

- real BAML prompt files and generated-client dispatch;
- validated Python data models using Pydantic v2;
- flat chapter pointers (`pointers: list[str]`), not grouped pointer headings;
- incremental element registration with stable internal tokens;
- inline element reference tokens resolved at render time;
- report-order and introduction-last generation flows;
- a concrete Markdown renderer;
- explicit package initialization for environment/API-key validation;
- pytest-based tests with no live LLM calls in normal unit tests.

LaTeX/PDF rendering, discipline-specific report builders, and multi-chapter consistency checking are not part of the MVP.

## Goals

- Provide a reusable package for civil-engineering report chapter generation.
- Use BAML as the real prompt layer for three chapter roles:
  - `ReportIntroduction`
  - `ReportChapter`
  - `ReportConclusion`
- Keep the Python architecture small and direct.
- Let callers describe chapters with validated plain data.
- Support body-first generation while writing the introduction later.
- Keep figure/table numbering stable in final rendered output even when generation order differs from report order.
- Render a complete Markdown document without LaTeX dependencies.
- Fail clearly when required LLM/BAML environment configuration is missing.
- Keep unit tests deterministic by mocking BAML calls.

## Non-Goals

- No LaTeX or PDF rendering in the MVP.
- No Word/HTML renderer in the MVP.
- No discipline-specific chapter-builder library in the MVP.
- No automatic calculation/domain-data gathering.
- No multi-chapter factual consistency checking.
- No live LLM calls in the normal test suite.
- No import-time API-key validation or package initialization side effects.

## Existing Codebase Context

Repository evidence at design time:

- `pyproject.toml` exists and defines package `forelius`, Python `>=3.12`, and no dependencies.
- `forelius/__init__.py` exists and is empty.
- `tests/__init__.py` exists and is empty.
- `README.md` exists and is empty.
- No implementation modules exist yet under `forelius/`.
- No `baml_src/` or `baml_client/` exists yet.
- No test runner is configured yet.
- The supplied planning input is `project-forelius-design-doc.md`.

Important adaptation from the draft: the draft showed a nested package layout (`forelius/forelius/`), but this repository already has top-level `forelius/` as the Python package root. The MVP must use the existing package root.

## Relevant Files and Modules

Existing files to update:

- `pyproject.toml`
- `forelius/__init__.py`

New source files/directories:

- `baml_src/`
- `baml_src/clients.baml`
- `baml_src/report/shared.baml`
- `baml_src/report/introduction.baml`
- `baml_src/report/chapter.baml`
- `baml_src/report/conclusion.baml`
- `baml_client/` if generated/required by BAML tooling
- `forelius/initialization.py`
- `forelius/config.py`
- `forelius/chapter.py`
- `forelius/elements.py`
- `forelius/section.py`
- `forelius/generator.py`
- `forelius/render/__init__.py`
- `forelius/render/base.py`
- `forelius/render/markdown.py`

New test files:

- `tests/test_initialization.py`
- `tests/test_models.py`
- `tests/test_elements.py`
- `tests/test_section.py`
- `tests/test_generator.py`
- `tests/test_markdown_renderer.py`
- `tests/test_baml_contracts.py`

## Accepted Design Decisions

### Decision 1: MVP boundary and dependency posture

Status: Accepted with assumptions.

- Include real BAML integration.
- Exclude LaTeX.
- Implement a simple Markdown renderer.
- Add dependencies only where needed for BAML, validated models, and tests.

### Decision 2: Repository package layout

Status: Accepted.

Use root-level BAML directories and the existing `forelius/` Python package:

```text
baml_src/
baml_client/        # generated if required
forelius/
tests/
```

Do not create `forelius/forelius/`.

### Decision 3: Core data model

Status: Accepted.

Use Pydantic v2 models. Use a flat chapter pointer list:

```python
pointers: list[str]
```

Do not implement `PointerGroup` or `PointerGroup.heading` in the MVP.

### Decision 4: BAML integration boundary

Status: Accepted.

Keep architecture simple: `ChapterGenerator` directly dispatches to generated BAML functions by `ChapterRole`. Tests should mock this dispatch path and must not call the live LLM.

### Decision 5: Element registry and token parsing

Status: Accepted.

Use incremental registration with stable internal tokens. Tokens are not final display numbers.

Placement tokens:

```text
<<FIG:fig_0001>>
<<TBL:tbl_0001>>
```

Inline reference tokens:

```text
<<REF:fig_0001>>
<<REF:tbl_0001>>
```

The renderer assigns final visible figure/table numbers from the final section order.

### Decision 6: Batch and interactive generation orchestration

Status: Accepted.

`ChapterSpec` order defines final report order. Generation order can differ via:

- `GenerationOrder.REPORT`
- `GenerationOrder.INTRODUCTION_LAST`

`generate_report()` must return sections in final report order even when generation occurred in a different order. Interactive callers can use `order_sections(sections, generation_order)` to apply the same generation-order-aware sorting before rendering.

### Decision 7: Markdown rendering boundary

Status: Accepted.

Implement a built-in simple `MarkdownRenderer` behind a `ReportRenderer` protocol. `Plot` and `Table` include a `caption`, and the renderer uses this caption for final numbered labels.

### Decision 8: Testing and validation strategy

Status: Accepted.

Use `pytest`. Normal tests must not perform live LLM calls. Add BAML contract tests/fixtures for the shared prompt core and every BAML function so prompts can be context-engineered later.

### Decision 9: Package initialization and API-key validation

Status: Accepted with assumptions.

Expose explicit initialization, e.g. `forelius.initialize()`, to validate required BAML/LLM environment variables before real generation. Do not validate API keys at import time and do not perform live LLM calls during initialization.

If required environment variables are missing, initialization must raise `ForeliusConfigurationError`. A simple exception-based failure mode is sufficient for the MVP.

The exact required environment variable names are implementation-dependent because the repository currently has no BAML provider configuration. The implementation must align initialization validation with `baml_src/clients.baml`.

## Proposed Architecture

### High-level flow

```text
Caller builds ReportConfig + ordered list[ChapterSpec]
          |
          v
chapter_generators(config, specs, generation_order=...)
  - derives final outline from specs order
  - creates shared ElementRegistry
  - yields ChapterGenerator objects in requested generation order
          |
          v
ChapterGenerator.generate()
  - registers/resolves this chapter's elements incrementally
  - builds BAML ChapterInput payload
  - dispatches to BAML function by ChapterRole
  - parses returned text into Section
          |
          v
list[Section]
  - generate_report() or order_sections() sorts back to final report order
          |
          v
MarkdownRenderer.render(config, sections)
  - assigns visible figure/table numbers from final section order
  - replaces inline <<REF:...>> tokens
  - replaces placement-token lines with Markdown element blocks
          |
          v
Markdown string
```

### Package layout

```text
baml_src/
  clients.baml
  report/
    shared.baml
    introduction.baml
    chapter.baml
    conclusion.baml

baml_client/                  # generated if required by BAML tooling

forelius/
  __init__.py
  initialization.py
  config.py
  chapter.py
  elements.py
  section.py
  generator.py
  render/
    __init__.py
    base.py
    markdown.py

tests/
  test_initialization.py
  test_models.py
  test_elements.py
  test_section.py
  test_generator.py
  test_markdown_renderer.py
  test_baml_contracts.py
```

## Data Flow

### 1. Caller input

The caller creates:

- one `ReportConfig`;
- an ordered `list[ChapterSpec]` in final report order.

Example conceptual input:

```python
config = ReportConfig(
    discipline="geotechnical engineer",
    subject="pile foundation calculation",
    language="Dutch",
    figure_label="Figuur",
    table_label="Tabel",
)

specs = [
    ChapterSpec(role=ChapterRole.INTRODUCTION, title="Inleiding", pointers=[...]),
    ChapterSpec(role=ChapterRole.BODY, title="Uitgangspunten", pointers=[...], elements=[...]),
    ChapterSpec(role=ChapterRole.CONCLUSION, title="Conclusie", pointers=[...]),
]
```

### 2. Outline derivation

`chapter_generators()` derives final chapter references from `specs` order:

```text
1. Inleiding
2. Uitgangspunten
3. Conclusie
```

The implementation should avoid mutating the caller's original `ReportConfig` in place. Prefer creating a runtime copy with `outline` populated.

### 3. Generation order

If `GenerationOrder.REPORT`, yield generators in final report order.

If `GenerationOrder.INTRODUCTION_LAST`, yield non-introduction chapters first and introduction chapters last while preserving each chapter's original `ChapterRef` number.

### 4. Element registration

Elements are registered incrementally when a chapter is generated.

For each element, `ElementRegistry` assigns a stable internal ID:

- figures: `fig_0001`, `fig_0002`, ...
- tables: `tbl_0001`, `tbl_0002`, ...

The registry returns BAML-facing element metadata containing:

- internal ID;
- kind (`figure` or `table`);
- caption;
- placement token;
- reference token.

### 5. BAML generation

`ChapterGenerator.generate()` sends BAML a structured input including:

- report config;
- full report outline;
- current chapter reference;
- flat `pointers`;
- BAML-facing report elements.

The selected BAML function returns Markdown-like chapter text. The prompt must instruct the model to:

- start with exactly one top-level markdown header for the chapter;
- use placement tokens on their own lines for element insertion;
- use inline `<<REF:...>>` tokens when referring to figures/tables;
- not invent visible figure/table numbers;
- not render tables or figures itself.

### 6. Parsing

`parse_section()` validates and maps generated text.

Responsibilities:

- detect placement-token-only lines;
- map each placement line to the expected `Plot` or `Table`;
- validate every expected placement token appears exactly once;
- reject duplicate placement tokens;
- reject unknown placement tokens;
- reject unknown inline `<<REF:...>>` tokens;
- preserve the text for rendering.

### 7. Rendering

`MarkdownRenderer.render(config, sections)` receives final-order sections. For batch usage, `generate_report()` returns final-order sections. For interactive usage, callers should pass accepted sections through `order_sections(sections, generation_order)` before rendering if they collected sections in generation order.

It should perform two logical passes:

1. Walk sections in order and assign visible figure/table numbers to all placed elements.
2. Render each line:
   - replace inline reference tokens with labels such as `Figure 1` or `Tabel 2`;
   - replace placement-token lines with Markdown image/table blocks and numbered captions;
   - preserve ordinary text.

## API / Interface Changes

### Public initialization API

`forelius/__init__.py` should export:

```python
initialize
ForeliusStatus
ForeliusConfigurationError
```

`forelius/initialization.py` should define:

```python
class ForeliusConfigurationError(Exception): ...

class ForeliusStatus(BaseModel):
    initialized: bool
    required_environment: list[str]


def initialize(required_environment: list[str] | None = None) -> ForeliusStatus: ...
def ensure_initialized() -> ForeliusStatus: ...
```

Implementation requirements:

- Use `os.environ` as the source of truth.
- Do not make a live LLM call.
- Do not run automatically at import time.
- If `required_environment` is `None`, use the default environment variable list aligned with `baml_src/clients.baml`.
- If required variables are missing, raise `ForeliusConfigurationError`. Do not return a partial success status for missing configuration.
- `ChapterGenerator` should ensure initialization before real BAML dispatch. Prefer calling `ensure_initialized()` inside the real `_dispatch()` path so generator tests can mock `_dispatch()` without requiring API keys.

Unknown: exact API-key variable names. This must be finalized when `baml_src/clients.baml` is implemented.

### Public config models

`forelius/config.py`:

```python
class ChapterRef(BaseModel):
    number: int
    title: str

class ReportConfig(BaseModel):
    discipline: str
    subject: str
    language: str
    figure_label: str
    table_label: str
    outline: list[ChapterRef] = Field(default_factory=list)
```

Use Pydantic v2 validation with `BaseModel` and `Field(default_factory=list)`.

### Public chapter models

`forelius/chapter.py`:

```python
class ChapterRole(str, Enum):
    INTRODUCTION = "introduction"
    BODY = "body"
    CONCLUSION = "conclusion"

class ChapterSpec(BaseModel):
    role: ChapterRole
    title: str
    pointers: list[str] = Field(default_factory=list)
    elements: list[Plot | Table] = Field(default_factory=list)

    def with_feedback(self, feedback: str) -> "ChapterSpec": ...
```

`with_feedback()` should return a new `ChapterSpec` with the feedback appended to `pointers`, preserving the same element objects.

### Public element models

`forelius/elements.py`:

```python
class ElementKind(str, Enum):
    FIGURE = "figure"
    TABLE = "table"

class Plot(BaseModel):
    caption: str
    path: str

class Table(BaseModel):
    caption: str
    headers: list[str]
    rows: list[list[str]]

class ReportElement(BaseModel):
    element_id: str
    kind: ElementKind
    caption: str
    placement_token: str
    reference_token: str
```

`Plot.caption` and `Table.caption` are the final rendered caption text. BAML may expose the same value as a description/caption in prompts.

`Table` validation should ensure every row has the same length as `headers`.

### Registry interface

`forelius/elements.py`:

```python
class ElementRegistry:
    def register_all(self, items: list[Plot | Table]) -> None: ...
    def resolve(self, items: list[Plot | Table]) -> list[ResolvedElement]: ...
```

The implementation may define an internal `ResolvedElement` model/dataclass containing:

- original `Plot | Table` object;
- `ReportElement` BAML metadata.

Registry requirements:

- Registration is incremental.
- Re-registering the same element object is idempotent.
- Use object identity (`id(element)`) or another stable internal mapping; do not require Pydantic models to be hashable.
- Use independent counters or prefixes to create IDs:
  - `fig_0001`, `fig_0002`, ...
  - `tbl_0001`, `tbl_0002`, ...
- Placement token format:
  - figures: `<<FIG:fig_0001>>`
  - tables: `<<TBL:tbl_0001>>`
- Reference token format:
  - `<<REF:fig_0001>>`
  - `<<REF:tbl_0001>>`

### Section parser interface

`forelius/section.py`:

```python
class Section(BaseModel):
    chapter: ChapterRef
    text: str
    line_element_map: dict[int, ResolvedElement]


def parse_section(
    chapter: ChapterRef,
    text: str,
    elements: list[ResolvedElement],
) -> Section: ...
```

Use Pydantic v2 for `Section` as well. If `ResolvedElement` contains internal non-Pydantic objects, configure the model with Pydantic v2's arbitrary-type support rather than switching `Section` to a dataclass.

Line numbers must be zero-based line indexes because Python line iteration is zero-based. Test this behavior explicitly.

### Generation interface

`forelius/generator.py`:

```python
class GenerationOrder(str, Enum):
    REPORT = "report"
    INTRODUCTION_LAST = "introduction_last"

class ChapterGenerator:
    config: ReportConfig
    chapter: ChapterRef
    spec: ChapterSpec
    registry: ElementRegistry

    def generate(self) -> Section: ...
    def draft(self) -> ChapterDraft: ...
    def _dispatch(self, role: ChapterRole, chapter_input: Any) -> str: ...

class ChapterDraft:
    def current(self) -> Section: ...
    def revise(self, feedback: str) -> Section: ...
    def accept(self) -> Section: ...

def chapter_generators(
    config: ReportConfig,
    specs: list[ChapterSpec],
    generation_order: GenerationOrder = GenerationOrder.REPORT,
) -> Iterator[ChapterGenerator]: ...

def order_sections(
    sections: list[Section],
    generation_order: GenerationOrder = GenerationOrder.REPORT,
) -> list[Section]: ...

def generate_report(
    config: ReportConfig,
    specs: list[ChapterSpec],
    generation_order: GenerationOrder = GenerationOrder.REPORT,
) -> list[Section]: ...
```

Implementation requirements:

- `specs` order is final report order.
- Derived `ChapterRef` numbers come from `specs` order.
- `chapter_generators()` yields according to `generation_order`.
- `order_sections()` applies final report ordering based on the supplied `GenerationOrder`: for `GenerationOrder.REPORT`, it preserves the provided order; for `GenerationOrder.INTRODUCTION_LAST`, it sorts by `Section.chapter.number` before rendering.
- `generate_report()` calls `order_sections(sections, generation_order)` before returning.
- `ChapterDraft` eagerly generates the first draft.
- `ChapterDraft.revise(feedback)` uses `ChapterSpec.with_feedback(feedback)` and regenerates with the same registry.
- Interactive callers that collect accepted sections in generation order should call `order_sections(sections, generation_order)` before rendering.
- Real BAML dispatch should local-import the generated BAML client to keep non-generation imports usable.

### Renderer interface

`forelius/render/base.py`:

```python
class ReportRenderer(Protocol):
    def render(self, config: ReportConfig, sections: list[Section]) -> str: ...
```

`forelius/render/markdown.py`:

```python
class MarkdownRenderer:
    def render(self, config: ReportConfig, sections: list[Section]) -> str: ...
```

Markdown rendering requirements:

- Assign visible figure and table numbers from final section order.
- Use `config.figure_label` and `config.table_label` for visible labels.
- Replace `<<REF:...>>` inline tokens with visible labels.
- Replace placement-token-only lines with element blocks.
- Raise a clear error for unknown `REF` tokens.
- Preserve normal text lines.

Suggested simple figure output:

```markdown
![<caption>](<path>)

**<figure_label> <n>: <caption>**
```

Suggested simple table output:

```markdown
**<table_label> <n>: <caption>**

| Header A | Header B |
| --- | --- |
| value | value |
```

## Code Architecture Sketch

### Before

```text
forelius/
  __init__.py      # empty

tests/
  __init__.py      # empty
```

### After

```text
baml_src/
  clients.baml                         # new; BAML client/provider config
  report/
    shared.baml                        # new; shared BAML types and prompt core
    introduction.baml                  # new; ReportIntroduction
    chapter.baml                       # new; ReportChapter
    conclusion.baml                    # new; ReportConclusion

baml_client/                           # new/generated if BAML tooling requires it

forelius/
  __init__.py                          # existing; export public API
  initialization.py                    # new; env validation
  config.py                            # new; report config models
  chapter.py                           # new; chapter role/spec models
  elements.py                          # new; elements, tokens, registry
  section.py                           # new; Section and parse_section
  generator.py                         # new; generation orchestration and BAML dispatch
  render/
    __init__.py                        # new; renderer exports
    base.py                            # new; ReportRenderer protocol
    markdown.py                        # new; MarkdownRenderer

tests/
  test_initialization.py               # new
  test_models.py                       # new
  test_elements.py                     # new
  test_section.py                      # new
  test_generator.py                    # new
  test_markdown_renderer.py            # new
  test_baml_contracts.py               # new
```

## File-by-File Implementation Plan

### `pyproject.toml`

- Existing file.
- Purpose: project metadata and dependencies.
- Required changes:
  - Add Pydantic v2 for validated models.
  - Add BAML dependency/tooling according to the actual BAML Python package requirements.
  - Configure package discovery/build settings so generated `baml_client` is importable in local development and included or explicitly generated for distribution.
  - Add `pytest` as a test/development dependency using the repository's chosen dependency style.
- Key dependencies:
  - Pydantic v2.
  - BAML package/tooling, exact package name to verify from BAML docs.
  - pytest.
- Tests:
  - Running `pytest` should discover tests under `tests/`.

### `baml_src/clients.baml`

- New file.
- Purpose: BAML client/provider configuration.
- Required changes:
  - Define the LLM client used by Forelius MVP.
  - Configure API-key environment variable(s).
  - Keep env var names aligned with `forelius/initialization.py`.
- Key types/functions/classes: BAML client config only.
- Dependencies: BAML tooling.
- Tests:
  - BAML validation command if available.
  - Static contract test should verify referenced required env vars are documented in initialization tests or constants.

### `baml_src/report/shared.baml`

- New file.
- Purpose: shared BAML data types and prompt core.
- Required changes:
  - Define BAML classes equivalent to:
    - `ChapterRef`
    - `ReportConfig`
    - `ReportElement`
    - `ChapterInput`
  - Use flat `pointers: string[]`.
  - Define shared prompt core that explains:
    - report discipline/subject/language;
    - report outline;
    - current chapter only;
    - markdown header contract;
    - placement token contract;
    - inline reference token contract;
    - no visible figure/table numbering by the LLM;
    - no rendering of tables/figures by the LLM.
- Key BAML concepts:
  - `ReportElement` must include `element_id`, `kind`, `caption`, `placement_token`, `reference_token`.
- Dependencies: BAML tooling.
- Tests:
  - `tests/test_baml_contracts.py` should verify token instructions, shared fields, and the shared prompt core are present.

### `baml_src/report/introduction.baml`

- New file.
- Purpose: BAML function for introduction chapters.
- Required changes:
  - Define `ReportIntroduction(input: ChapterInput) -> string`.
  - Use shared prompt core.
  - Add introduction-specific framing: set scope/context, do not pre-empt results.
- Dependencies: shared BAML definitions.
- Tests:
  - Function-level BAML contract fixture/test for representative introduction input.

### `baml_src/report/chapter.baml`

- New file.
- Purpose: BAML function for body chapters.
- Required changes:
  - Define `ReportChapter(input: ChapterInput) -> string`.
  - Use shared prompt core.
  - Keep body chapter framing discipline-agnostic.
- Dependencies: shared BAML definitions.
- Tests:
  - Function-level BAML contract fixture/test for representative body chapter input with at least one figure and one table.

### `baml_src/report/conclusion.baml`

- New file.
- Purpose: BAML function for conclusion chapters.
- Required changes:
  - Define `ReportConclusion(input: ChapterInput) -> string`.
  - Use shared prompt core.
  - Add conclusion-specific framing: synthesize only from provided pointers and do not introduce new facts.
- Dependencies: shared BAML definitions.
- Tests:
  - Function-level BAML contract fixture/test for representative conclusion input.

### `baml_client/`

- New/generated directory if required by BAML tooling.
- Purpose: generated Python client for BAML functions.
- Required changes:
  - Generate according to BAML tooling.
  - Treat `baml_client` as a top-level generated Python package importable from the repository root.
  - Do not hand-edit generated files.
  - If distribution packaging is configured, include `baml_client` as a generated top-level package or document that it must be generated before runtime use.
- Key functions expected by Python code:
  - `ReportIntroduction`
  - `ReportChapter`
  - `ReportConclusion`
- Import expectation:
  - `forelius/generator.py` should use the actual generated top-level import path, for example `from baml_client import b` or the equivalent path produced by the configured BAML generator.
  - Keep this import local to `_dispatch()` so importing non-generation parts of `forelius` does not require a generated client.
- Dependencies: generated by BAML.
- Tests:
  - Dispatch tests patch generated functions through the exact import path used by `forelius/generator.py`.
  - A lightweight import/contract test should fail clearly if `baml_client` is not generated when BAML dispatch tests are enabled.

### `forelius/__init__.py`

- Existing file.
- Purpose: public package exports.
- Required changes:
  - Export initialization API.
  - Export primary data models and generation/rendering entry points where convenient.
  - Do not perform initialization at import time.
- Key exports:
  - `initialize`
  - `ForeliusStatus`
  - `ForeliusConfigurationError`
  - `ReportConfig`
  - `ChapterRef`
  - `ChapterRole`
  - `ChapterSpec`
  - `Plot`
  - `Table`
  - `generate_report`
  - `chapter_generators`
  - `order_sections`
  - `GenerationOrder`
  - `MarkdownRenderer`
- Dependencies: internal modules only.
- Tests:
  - Importing `forelius` without API keys must not fail.

### `forelius/initialization.py`

- New file.
- Purpose: explicit environment/API-key validation.
- Required changes:
  - Define `ForeliusConfigurationError`.
  - Define `ForeliusStatus`.
  - Define `initialize()` and `ensure_initialized()`.
  - Track package initialization status in module-level state.
  - Validate required environment variables from `os.environ`.
  - Do not perform network calls.
- Key implementation detail:
  - Default required environment variables must match BAML client config.
  - Because exact BAML provider config is unknown now, implementation must finalize the env var names while adding `clients.baml`.
- Dependencies: standard library and Pydantic v2.
- Tests:
  - Missing env vars raise `ForeliusConfigurationError`.
  - Present env vars succeed.
  - Importing package has no side effects.
  - No live LLM call occurs.

### `forelius/config.py`

- New file.
- Purpose: report-level validated models.
- Required changes:
  - Implement `ChapterRef` and `ReportConfig`.
  - Use safe list defaults via Pydantic v2 `Field(default_factory=list)`.
- Key types:
  - `ChapterRef`
  - `ReportConfig`
- Dependencies: validated model library.
- Tests:
  - Construct valid config.
  - Reject invalid types where validation supports it.
  - Outline default is not shared between instances.

### `forelius/chapter.py`

- New file.
- Purpose: chapter role and specification models.
- Required changes:
  - Implement `ChapterRole` enum.
  - Implement `ChapterSpec` with `pointers: list[str]`.
  - Implement `with_feedback()`.
- Key types:
  - `ChapterRole`
  - `ChapterSpec`
- Dependencies:
  - `forelius.elements.Plot`
  - `forelius.elements.Table`
- Tests:
  - Valid specs.
  - `with_feedback()` appends feedback and preserves elements.
  - No `PointerGroup` exists or is required by public APIs.

### `forelius/elements.py`

- New file.
- Purpose: figure/table models, BAML-facing report elements, token registry.
- Required changes:
  - Implement `ElementKind`.
  - Implement `Plot` with `caption` and `path`.
  - Implement `Table` with `caption`, `headers`, and `rows`.
  - Validate table row lengths.
  - Implement `ReportElement`.
  - Implement `ElementRegistry` and any internal `ResolvedElement` type.
- Key functions/classes:
  - `ElementRegistry.register_all()`
  - `ElementRegistry.resolve()`
- Dependencies: validated model library, standard library.
- Tests:
  - Incremental registration.
  - Idempotent registration of the same object.
  - Correct `fig_0001`/`tbl_0001` IDs.
  - Correct placement/reference tokens.
  - Table row length validation.

### `forelius/section.py`

- New file.
- Purpose: parsed chapter sections and token validation.
- Required changes:
  - Implement `Section`.
  - Implement `parse_section()`.
  - Define clear parser exceptions if useful, or use `ValueError` with clear messages.
- Key behavior:
  - Match placement-token-only lines.
  - Match inline `<<REF:...>>` tokens.
  - Validate expected placement tokens exactly once.
  - Reject duplicates and unknown tokens.
  - Preserve text.
- Dependencies:
  - `forelius.config.ChapterRef`
  - `forelius.elements.ResolvedElement`
- Tests:
  - Valid text with figure/table placements.
  - Missing placement token raises.
  - Duplicate placement token raises.
  - Unknown placement token raises.
  - Unknown inline reference raises.
  - Inline references are allowed for expected same-chapter elements.

### `forelius/generator.py`

- New file.
- Purpose: BAML-backed chapter generation, draft flow, report orchestration.
- Required changes:
  - Implement `GenerationOrder`.
  - Implement `ChapterGenerator`.
  - Implement `ChapterDraft`.
  - Implement `chapter_generators()`.
  - Implement `order_sections()`.
  - Implement `generate_report()`.
  - Directly dispatch to BAML generated functions in `_dispatch()`.
- Key behavior:
  - Derive outline from `specs` order.
  - Yield according to generation order.
  - Incrementally register/resolve elements per chapter.
  - Convert Python models into BAML-compatible input.
  - Parse returned text into `Section`.
  - Sort accepted sections by final chapter number through `order_sections()`.
  - Sort `generate_report()` output by final chapter number.
  - Ensure initialization before real BAML dispatch.
- Dependencies:
  - `forelius.initialization.ensure_initialized`
  - `forelius.config`
  - `forelius.chapter`
  - `forelius.elements`
  - `forelius.section`
  - generated `baml_client` in `_dispatch()` only.
- Tests:
  - Report-order generation.
  - Introduction-last generation.
  - `order_sections()` final ordering for `GenerationOrder.REPORT` and `GenerationOrder.INTRODUCTION_LAST`.
  - `generate_report()` final ordering.
  - Draft current/revise/accept.
  - `_dispatch()` role routing with patched generated BAML functions.
  - Generator tests should mock `_dispatch()` for normal orchestration tests.

### `forelius/render/__init__.py`

- New file.
- Purpose: renderer package exports.
- Required changes:
  - Export `ReportRenderer` and `MarkdownRenderer`.
- Dependencies: renderer modules.
- Tests:
  - Import works.

### `forelius/render/base.py`

- New file.
- Purpose: renderer protocol.
- Required changes:
  - Define `ReportRenderer` protocol.
- Key interface:
  - `render(config: ReportConfig, sections: list[Section]) -> str`
- Dependencies: `typing.Protocol`.
- Tests:
  - Covered by renderer import/use tests.

### `forelius/render/markdown.py`

- New file.
- Purpose: concrete Markdown renderer.
- Required changes:
  - Implement `MarkdownRenderer.render()`.
  - Assign final visible numbers.
  - Replace placement tokens.
  - Replace inline reference tokens.
  - Render simple images and tables.
- Key functions/classes:
  - `MarkdownRenderer`
  - private helpers for numbering, reference replacement, figure rendering, table rendering.
- Dependencies:
  - `forelius.config.ReportConfig`
  - `forelius.section.Section`
  - `forelius.elements.Plot`, `Table`
- Tests:
  - Figure rendering.
  - Table rendering.
  - Inline reference replacement.
  - Unknown reference handling.
  - Introduction generated last but rendered first numbering.

### `tests/test_initialization.py`

- New file.
- Purpose: initialization behavior.
- Required tests:
  - Importing `forelius` does not require API keys.
  - `initialize()` succeeds when required env vars are present.
  - `initialize()` raises `ForeliusConfigurationError` when vars are missing.
  - `ensure_initialized()` behavior is deterministic.

### `tests/test_models.py`

- New file.
- Purpose: validated data models.
- Required tests:
  - `ReportConfig`, `ChapterRef`, `ChapterSpec`, `Plot`, `Table` construction.
  - Invalid table row lengths.
  - `ChapterSpec.with_feedback()`.

### `tests/test_elements.py`

- New file.
- Purpose: registry/token behavior.
- Required tests:
  - Incremental registration.
  - Idempotent same-object registration.
  - Token formats.
  - Separate figure/table prefixes.

### `tests/test_section.py`

- New file.
- Purpose: parser behavior.
- Required tests:
  - Placement-token mapping.
  - Missing token error.
  - Duplicate token error.
  - Unknown placement token error.
  - Unknown inline reference token error.

### `tests/test_generator.py`

- New file.
- Purpose: orchestration and dispatch behavior.
- Required tests:
  - `chapter_generators()` derives final outline.
  - `GenerationOrder.REPORT` yields report order.
  - `GenerationOrder.INTRODUCTION_LAST` yields introductions last.
  - `order_sections()` returns final report order.
  - `generate_report()` returns final report order.
  - `ChapterDraft` revise flow.
  - `_dispatch()` routes roles to BAML functions using patches/mocks.
- Do not call live BAML/LLM.

### `tests/test_markdown_renderer.py`

- New file.
- Purpose: Markdown output.
- Required tests:
  - Figure output and caption.
  - Table output and caption.
  - Render-time numbering.
  - Inline `REF` replacement.
  - Unknown `REF` failure.

### `tests/test_baml_contracts.py`

- New file.
- Purpose: BAML prompt/function contract coverage without live LLM calls.
- Required tests:
  - Every expected BAML function exists in source:
    - `ReportIntroduction`
    - `ReportChapter`
    - `ReportConclusion`
  - Shared BAML schema includes flat `pointers`.
  - Shared BAML schema includes element fields:
    - `element_id`
    - `kind`
    - `caption`
    - `placement_token`
    - `reference_token`
  - Shared prompt core exists and is used by all three BAML functions.
  - Prompt source includes instructions for:
    - markdown chapter header;
    - placement tokens on their own line;
    - inline reference tokens;
    - no visible figure/table numbering by the LLM;
    - no model-rendered tables/figures.
  - Add representative fixtures for each BAML function input to support future context engineering.

If BAML provides native test syntax/commands, mirror these function-level fixtures in the BAML-native test format as well. Keep normal CI/local tests offline unless an explicit live-LLM test mode is later added.

## Testing Strategy

### Unit tests

Use `pytest`.

Primary command:

```bash
pytest
```

Expected unit test coverage:

- initialization and environment validation;
- validated model construction and validation;
- element registry ID/token behavior;
- section parsing and error cases;
- generation-order orchestration;
- draft revision flow;
- BAML dispatch routing with mocks;
- Markdown renderer numbering/replacement/output.

### Integration tests

MVP integration tests should still avoid live LLM calls.

Recommended integration-style tests:

- `generate_report()` with mocked BAML text output and Markdown rendering end-to-end.
- Introduction-last generation with final report-order rendering.
- Figure/table reference replacement across final ordered sections.

### BAML function and shared prompt contract tests

Add BAML contract tests/fixtures for the shared prompt core and every BAML function:

- shared prompt core in `shared.baml`;
- `ReportIntroduction`;
- `ReportChapter`;
- `ReportConclusion`.

These tests are for prompt contract/context-engineering support and should be deterministic. They may be static source/fixture tests if BAML tooling does not provide an offline prompt-rendering test command.

### Regression tests

Add regression tests for:

- missing placement token;
- duplicated placement token;
- unknown inline reference token;
- introduction generated last but rendered first;
- feedback revisions preserving element tokens;
- importing package without API keys.

### Fixtures

Recommended fixtures:

- simple `ReportConfig` using English labels;
- simple `ReportConfig` using Dutch labels;
- one `Plot` fixture;
- one `Table` fixture;
- body chapter text containing placement and reference tokens;
- one shared prompt-core contract fixture;
- three BAML input fixtures, one per BAML function.

### Validation commands

Known command from current repo: none configured yet.

Required after implementation:

```bash
pytest
```

BAML validation command: unknown at design time because BAML is not yet configured in the repository. The implementation agent must identify and document the correct command from the chosen BAML tooling. If available, add it to the validation checklist and README later.

## Migration / Backward Compatibility

Not applicable for existing users because the repository currently has no implemented public API.

Compatibility constraints for the MVP implementation:

- Keep `forelius/` as the Python package root.
- Do not introduce the nested `forelius/forelius/` layout.
- Do not require API keys merely to import `forelius`.
- Do not require live LLM calls for unit tests.
- Do not implement `PointerGroup` in the MVP public API.

## Risks and Mitigations

### Risk: BAML dependency and generated client path are unknown

- Why it matters: `_dispatch()` depends on generated BAML function imports.
- Mitigation:
  - Keep generated-client imports local to `_dispatch()`.
  - Patch the exact import path in tests after BAML generation is configured.
  - Document the verified BAML command in implementation notes/README later.

### Risk: Required API-key environment variable names are unknown

- Why it matters: `initialize()` must validate the same variables used by BAML.
- Mitigation:
  - Finalize env var names when implementing `baml_src/clients.baml`.
  - Keep required env vars centralized in `forelius/initialization.py`.
  - Add tests proving initialization and BAML config stay aligned as far as practical.

### Risk: LLM may omit or alter tokens

- Why it matters: rendering depends on exact placement and reference tokens.
- Mitigation:
  - Prompts must strongly instruct exact token usage.
  - `parse_section()` fails fast on missing/duplicate/unknown placement tokens.
  - Renderer fails on unknown references.
  - BAML contract tests assert token instructions remain present.

### Risk: Generated text may include visible figure/table numbers

- Why it matters: renderer assigns final numbers; model-invented numbers may conflict.
- Mitigation:
  - BAML prompt explicitly forbids visible numbering by the model.
  - Prompt instructs use of `<<REF:...>>` tokens instead.
  - Context-engineering fixtures should include examples using `REF` tokens.

### Risk: Incremental registry uses object identity

- Why it matters: equivalent copied element objects would receive different tokens.
- Mitigation:
  - Document that draft revisions preserve the same element instances.
  - `ChapterSpec.with_feedback()` must preserve `elements` as-is.
  - Future versions can add explicit user-provided element IDs if needed.

### Risk: Markdown renderer is too simple for production reports

- Why it matters: civil-engineering reports may need rich formatting.
- Mitigation:
  - MVP intentionally targets simple Markdown.
  - Renderer is behind a protocol so richer renderers can be added later.

## Validation Checklist

Implementation is complete when all applicable items pass:

- [ ] `forelius/` remains the Python package root.
- [ ] `baml_src/` is at repository root.
- [ ] No nested `forelius/forelius/` package is created.
- [ ] `pyproject.toml` includes Pydantic v2, pytest, and required BAML dependencies.
- [ ] `forelius.initialize()` exists and is exported.
- [ ] Importing `forelius` does not require API keys.
- [ ] `ChapterSpec` uses `pointers: list[str]`; no MVP `PointerGroup` is required.
- [ ] Element placement tokens use stable internal IDs, not final numbers.
- [ ] Inline `<<REF:...>>` tokens are supported.
- [ ] Parser validates missing, duplicate, and unknown tokens.
- [ ] `GenerationOrder.INTRODUCTION_LAST` works.
- [ ] `generate_report()` returns final report order.
- [ ] Markdown renderer assigns final visible numbering from section order.
- [ ] BAML files define `ReportIntroduction`, `ReportChapter`, and `ReportConclusion`.
- [ ] BAML prompt contracts include shared prompt core usage plus header, placement-token, and reference-token instructions.
- [ ] Unit tests do not make live LLM calls.
- [ ] `pytest` passes.
- [ ] BAML validation command is identified if available.

## Implementation Execution Plan

### Phase 1: Project tooling and dependencies

1. Update `pyproject.toml`.
2. Add required dependencies:
   - Pydantic v2;
   - pytest;
   - BAML dependency/tooling, using the package and configuration required by the selected BAML version.
3. Configure package discovery/build settings so `forelius` and generated `baml_client` are importable in local development.
4. Decide and document generated-client runtime behavior:
   - either include generated `baml_client` in distribution packaging;
   - or clearly document that `baml_client` must be generated before runtime use.
5. Confirm the package imports without API keys:

```bash
python -c "import forelius"
```

6. Confirm pytest discovery works:

```bash
pytest
```

At this phase, tests may be minimal, but the command should run.

### Phase 2: Core models

Implement foundational models before orchestration, parsing, rendering, or BAML dispatch.

Files:

```text
forelius/config.py
forelius/elements.py
forelius/chapter.py
```

Implement:

- `ReportConfig`;
- `ChapterRef`;
- `ChapterRole`;
- `ChapterSpec`;
- `Plot`;
- `Table`;
- `ReportElement`;
- `ElementKind`.

Required model behavior:

- use Pydantic v2 models and `Field(default_factory=list)` for list defaults;
- validate that every `Table.rows` entry has the same length as `Table.headers`;
- implement `ChapterSpec.with_feedback()` so it appends feedback while preserving the same element objects.

Add/complete tests:

```text
tests/test_models.py
```

Model tests must include invalid table row-length validation and `ChapterSpec.with_feedback()` behavior.

### Phase 3: Initialization

Implement explicit initialization before real BAML dispatch exists.

Files:

```text
forelius/initialization.py
forelius/__init__.py
```

Implement initialization API:

- `initialize()`;
- `ensure_initialized()`;
- `ForeliusStatus`;
- `ForeliusConfigurationError`.

Also update public package exports in `forelius/__init__.py` so the main MVP API is importable from `forelius`:

- `ReportConfig`;
- `ChapterRef`;
- `ChapterRole`;
- `ChapterSpec`;
- `Plot`;
- `Table`;
- `chapter_generators`;
- `generate_report`;
- `order_sections`;
- `GenerationOrder`;
- `MarkdownRenderer`.

Required behavior:

- importing `forelius` must not require API keys;
- missing required environment variables must raise `ForeliusConfigurationError`;
- initialization must not make live LLM/network calls.

Add/complete tests:

```text
tests/test_initialization.py
```

### Phase 4: Element registry and token generation

Implement registry behavior before parsing or rendering.

File:

```text
forelius/elements.py
```

Implement:

- `ElementRegistry`;
- internal `ResolvedElement`;
- stable IDs:
  - `fig_0001`;
  - `tbl_0001`;
- placement tokens:
  - `<<FIG:fig_0001>>`;
  - `<<TBL:tbl_0001>>`;
- reference tokens:
  - `<<REF:fig_0001>>`;
  - `<<REF:tbl_0001>>`.

Add/complete tests:

```text
tests/test_elements.py
```

### Phase 5: Section parser

Implement parsing after token generation exists.

File:

```text
forelius/section.py
```

Implement:

- `Section`;
- `parse_section()`.

Required validation:

- every expected placement token appears exactly once;
- duplicate placement tokens raise;
- unknown placement tokens raise;
- unknown inline `REF` tokens raise;
- line indexes are zero-based.

Add/complete tests:

```text
tests/test_section.py
```

### Phase 6: Markdown renderer

Implement rendering before BAML so end-to-end package behavior can be tested with fake generated text.

Files:

```text
forelius/render/__init__.py
forelius/render/base.py
forelius/render/markdown.py
```

Implement:

- `ReportRenderer`;
- `MarkdownRenderer`.

Renderer responsibilities:

- assign visible figure/table numbers from final section order;
- replace inline `<<REF:...>>` tokens;
- replace placement-token lines;
- render simple Markdown images and tables;
- raise clearly for unknown references.

Add/complete tests:

```text
tests/test_markdown_renderer.py
```

### Phase 7: Generator orchestration without real BAML

Implement orchestration with mocked `_dispatch()` first. Do not integrate live BAML yet.

File:

```text
forelius/generator.py
```

Implement:

- `GenerationOrder`;
- `ChapterGenerator`;
- `ChapterDraft`;
- `chapter_generators()`;
- `order_sections()`;
- `generate_report()`.

Test using fake generated text only.

Add/complete tests:

```text
tests/test_generator.py
```

Cover:

- report-order generation;
- introduction-last generation;
- `chapter_generators()` deriving the outline without mutating the caller's original `ReportConfig`;
- `order_sections()` behavior for supported generation orders;
- `generate_report()` returning final report order;
- draft revise/accept flow.

### Phase 8: BAML source files

Add BAML after Python orchestration is stable.

Files:

```text
baml_src/clients.baml
baml_src/report/shared.baml
baml_src/report/introduction.baml
baml_src/report/chapter.baml
baml_src/report/conclusion.baml
```

Implement:

- BAML client/provider configuration;
- shared BAML types;
- shared prompt core;
- `ReportIntroduction`;
- `ReportChapter`;
- `ReportConclusion`.

Align `clients.baml` environment variables with `forelius/initialization.py`.

### Phase 9: Generated BAML client integration

Generate or configure:

```text
baml_client/
```

Then update:

```text
forelius/generator.py
```

Implement real `_dispatch()` with local imports of generated BAML functions.

Test with patched generated functions only. Do not call live LLMs in normal tests.

Role-routing tests must verify:

- `ChapterRole.INTRODUCTION` dispatches to `ReportIntroduction`;
- `ChapterRole.BODY` dispatches to `ReportChapter`;
- `ChapterRole.CONCLUSION` dispatches to `ReportConclusion`.

### Phase 10: BAML contract tests

Add/complete:

```text
tests/test_baml_contracts.py
```

Validate:

- shared prompt core exists;
- all three BAML functions exist;
- shared schema includes required fields:
  - `element_id`;
  - `kind`;
  - `caption`;
  - `placement_token`;
  - `reference_token`;
- prompts include token/header/reference instructions;
- representative fixtures exist for the shared prompt core and each BAML function.

If BAML provides an offline/native test mechanism, mirror these fixtures there as well.

### Phase 11: End-to-end offline test

Add one offline integration-style test:

1. Build a `ReportConfig`.
2. Build multiple `ChapterSpec`s.
3. Mock BAML output.
4. Generate sections with `GenerationOrder.INTRODUCTION_LAST`.
5. Sort sections through `order_sections()` or use `generate_report()`.
6. Render Markdown.
7. Assert final chapter order and figure/table numbering.

### Phase 12: Final validation

Run:

```bash
pytest
```

Then, if BAML tooling provides a validation command, run the discovered BAML validation command.

Final checklist for this phase:

- package imports without API keys;
- initialization raises clearly when env vars are missing;
- no normal tests call live LLMs;
- Markdown renderer works;
- generator ordering works;
- BAML contract tests pass;
- BAML validation command is documented if available;
- unresolved assumptions in this design remain explicitly documented.

## Open Questions

### Exact BAML dependency/tooling command

- Unknown: the repository currently has no BAML setup.
- Why it matters: implementation needs the correct dependency, generated client path, and validation command.
- Conservative default: add BAML using the official/current BAML Python tooling and keep imports isolated in `_dispatch()`.
- Status: Accepted with assumptions.

### Exact generated BAML client import path

- Unknown: no generated client exists yet.
- Why it matters: `ChapterGenerator._dispatch()` must import the generated functions.
- Conservative default: use the import path produced by the configured BAML generator and test it with patched dispatch tests.
- Status: Accepted with assumptions.

### Exact LLM API-key environment variable name

- Unknown: provider/client is not configured yet.
- Why it matters: `initialize()` must validate the same env vars that BAML uses.
- Conservative default: centralize required env vars in `forelius/initialization.py` and align them with `baml_src/clients.baml` during implementation.
- Status: Accepted with assumptions.

## Implementability Check

- Referenced existing files verified during reconnaissance:
  - `pyproject.toml` exists.
  - `forelius/__init__.py` exists.
  - `tests/__init__.py` exists.
  - `project-forelius-design-doc.md` exists as source input.
- All other source files listed above are explicitly marked as new or generated.
- Proposed structure fits the current repository because it uses the existing top-level `forelius/` package and root-level `tests/`.
- Root-level `baml_src/` avoids nesting BAML prompt files inside the Python package.
- Root-level generated `baml_client/` is explicitly treated as a top-level generated package with local imports isolated to BAML dispatch.
- Dependency additions are justified:
  - Pydantic v2 validated models for public API validation;
  - BAML for required LLM prompt layer;
  - pytest for deterministic tests.
- Interfaces match the accepted MVP simplifications:
  - flat `pointers`;
  - no `PointerGroup`;
  - direct BAML dispatch;
  - Markdown renderer only.
- Test locations match the existing `tests/` layout.
- Validation command `pytest` is specified; BAML validation command remains tool-dependent and is called out as an open question.
- Pydantic v2 is now fixed as the validation-model dependency; the implementation agent does not need to choose a validation framework.
- No critical accepted decision is hidden; all nine decisions and the post-review clarifications are represented in this document.
- Suggested implementation order:
  1. Add dependencies and model files.
  2. Add initialization.
  3. Add elements/registry.
  4. Add section parser.
  5. Add Markdown renderer.
  6. Add generator orchestration with mocked dispatch tests.
  7. Add BAML source files and generated client integration.
  8. Add BAML contract tests/fixtures.
  9. Run `pytest` and BAML validation if available.
