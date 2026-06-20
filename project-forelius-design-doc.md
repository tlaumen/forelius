# Project Forelius — Design Document

**Status:** Draft v0.3.2
**Date:** 2026-06-18
**Package name:** `forelius`

## 1. Summary

Forelius is a standalone, discipline-agnostic package for generating civil
engineering report chapters with an LLM. It generalizes a set of six
bespoke BAML functions originally written for geotechnical pile-foundation
reports (introduction, soil investigation, assumptions, modelling, results,
conclusion) into three reusable functions plus a small Python orchestration
layer. The goal is a package any civil engineering discipline — structural,
hydraulic, geotechnical, pavement — can plug domain content into without
touching the underlying prompts.

The Python layer is organized around two levels of granularity:
`ChapterGenerator`, which owns the generation lifecycle of a single chapter
including interactive revision via `ChapterDraft`, and `chapter_generators`
plus `generate_report`, which compose individual generators into a full
report run.

## 2. Background

The originating implementation defined one BAML function per report
chapter. Each function repeated the same prompt skeleton: a fixed
seven-chapter Dutch geotechnical table of contents, a hardcoded "you are a
geotechnical engineer writing about a foundation calculation" framing, a
shared set of style rules, and a hardcoded instruction to write in Dutch.
The functions diverged in three places: the shape of the "pointers" input
(plain string lists for most chapters, bespoke structs for Modelling and
Results), an extra `parameters` field unique to the Assumptions chapter,
and a handful of one-off instructions embedded directly in the prompt text
(e.g. "explicitly link the ULS load to the design capacity").

Reviewing that implementation surfaced several issues worth fixing rather
than carrying forward as-is:

- Discipline, subject, language, and the report's table of contents were
  all hardcoded into every prompt, so a different discipline or a
  different-length report meant copying and editing a `.baml` file.
- The bespoke per-chapter pointer structs (`ModellingPointers`,
  `ResultPointers`) baked domain knowledge directly into the schema,
  which doesn't generalize to disciplines that weren't anticipated.
- Chapter-specific writing directives were scattered as free text inside
  individual prompts instead of being an explicit, reusable input.
- The downstream Python parser expects every chapter to open with a
  single markdown `#` header, but no prompt actually instructs the model
  to produce one — the contract was implicit and undocumented.
- The figure/table marker tokens (`Figuur`, `Tabel`) were hardcoded Dutch
  strings baked into the prompt text rather than a parameter, coupling
  report language to report structure.
- The Conclusion chapter's input class omitted the `elements` field
  entirely, an asymmetry with every other chapter that wasn't a
  deliberate design choice so much as an artifact of the original
  proof-of-concept.
- Dispatching to the correct function was done via `isinstance` checks
  on the input type, which only works because each chapter has its own
  type — a single shared input type (as proposed here) needs an explicit
  dispatch key instead.

## 3. Goals

- One shared, parameterized prompt skeleton powering three entry points:
  `ReportIntroduction`, `ReportChapter`, `ReportConclusion`.
- No discipline-, subject-, or language-specific text hardcoded into any
  prompt — all of it flows in through input data.
- A report's table of contents and chapter count are arbitrary and
  derived from whatever chapters the caller defines, not fixed at seven.
- The text-output contract (markdown header, figure/table markers) is
  explicitly instructed, not assumed.
- The caller assembles report content as plain `ChapterSpec` dataclasses
  using ordinary functions — no class hierarchy to implement.
- Both batch generation (all chapters in sequence, no interaction) and
  interactive generation (review and revise individual chapters before
  accepting) are supported through the same underlying infrastructure.
- The package has no dependency on any particular calling application's
  orchestration model — it consumes plain data and returns plain text
  plus a parsed section, full stop.

## 4. Non-Goals

- Forelius does not decide what counts as a chapter's content for a given
  discipline — that domain logic (what pointers to gather, what tables to
  build) lives entirely in caller-supplied code.
- Forelius does not handle PDF/LaTeX rendering itself beyond a reference
  implementation; rendering is behind a pluggable interface.
- Forelius does not attempt multi-chapter consistency checking (e.g.
  verifying the Conclusion doesn't contradict the Results chapter) in
  this version — chapters are generated independently in sequence.

## 5. Architecture Overview

Forelius has two layers. The BAML layer defines the shared types, a
reusable prompt fragment (`ChapterPromptCore`), and the three entry-point
functions. The Python layer is built around `ChapterGenerator` as the
core unit — it owns everything needed to generate one chapter, including
interactive revision. `chapter_generators` is the report-level primitive
that sets up shared infrastructure (outline derivation, element
pre-registration) and yields one `ChapterGenerator` per chapter.
`generate_report` is a one-liner convenience wrapper over
`chapter_generators` for the common batch case.

All `ChapterSpec`s are built upfront by the caller before any generation
begins, so element numbering is fully determined and any data problem
surfaces before a single LLM call is made.

```
caller builds list[ChapterSpec]
          |
          v
   chapter_generators(config, specs)
   - derives outline
   - creates ElementRegistry
   - pre-registers ALL elements across all specs
     (assigns sequential figure/table numbers for the whole report)
   - yields ChapterGenerator (one per chapter, in order)
          |
          +-----------------------------+
          |                             |
     batch path                  interactive path
          |                             |
   gen.generate()               gen.draft() -> ChapterDraft
          |                             |
          v                    draft.current() -> Section
       Section                 draft.revise(feedback) -> Section
                               draft.accept() -> Section
          |                             |
          +-----------------------------+
          |
    list[Section]
    (each Section contains text + line_element_map:
     line numbers → Plot/Table objects, built by parse_section
     from the <<FIG:X>> / <<TBL:X>> tokens the LLM placed in its output)
          |
   ReportRenderer.render(sections)
   - walks text lines in order
   - substitutes each <<FIG:X>> / <<TBL:X>> line with the rendered
     figure/table, composing the caption from ReportConfig.figure_label
     / table_label + the number extracted from the token
          |
          v
    final document
```

## 6. Design Decisions

**D1 — Three entry functions sharing one prompt fragment, not one
polymorphic function.** A single `ReportChapter(role, input)` function
was considered, since it would make looping over arbitrary chapters
trivial. It was rejected in favor of three named functions
(`ReportIntroduction`, `ReportChapter`, `ReportConclusion`) sharing a
`template_string` core, because Introduction and Conclusion appear
exactly once per report and benefit from genuinely different framing
("set the scope, don't pre-empt results" vs. "synthesize only what's
already been established"), and because keeping them separate leaves room
for their output contracts to diverge later (for example, a structured
`{summary, recommendations}` return type for Conclusion) without breaking
every other chapter's signature. `ReportChapter` remains the one function
called in a loop for however many body chapters a given report defines.

**D2 — A single `ReportConfig` object threaded through every call.**
Discipline, subject, language, the figure/table label words, and the
report outline are report-level, not chapter-level, so they're built once
per report and passed unchanged into every chapter call rather than
re-specified each time.

**D3 — The outline is derived, not declared.** Rather than maintaining an
outline list independently of the list of `ChapterSpec`s (and risking the
two drifting out of sync), `ReportConfig.outline` is computed
automatically inside `chapter_generators` from the order of specs the
caller provides. Each chapter only needs to know its own title; its
position in the table of contents is inferred.

**D4 — `PointerGroup` (heading + bullet items) replaces bespoke
per-chapter pointer structs.** The original `ModellingPointers` and
`ResultPointers` classes hardcoded a fixed set of named fields specific to
pile-foundation modelling, which has no obvious analogue in, say, a
pavement design report. A generic `PointerGroup { heading: string?,
items: string[] }[]` keeps the benefit of letting a chapter organize
information under headings the model can structure its writing around,
without requiring a new schema for every discipline. The cost is some
loss of compile-time structure compared to a typed `ResultPointers` class;
that's accepted as the price of genericity.

**D5 — No `additional_instructions` field.** A dedicated escape-hatch
field for per-chapter writing directives was considered and rejected.
Directives like "don't enumerate the parameters, just point at the table"
are domain knowledge that belongs in the pointers themselves — the same
channel through which everything the model should write about is
communicated. Adding a structurally separate field creates an implicit
two-tier content model (facts vs. instructions) without a reliable
mechanism to enforce it: there is no schema rule preventing a caller from
accidentally placing a writing directive in `pointer_groups` or a domain
fact in `additional_instructions`. The `PointerGroup.heading` field
already provides enough structure to distinguish writing-rule entries from
factual ones at the prompt level when needed. Chapter-specific behavioral
constraints that truly can't be expressed as pointers should be addressed
by extending the prompt template in a discipline-specific BAML function
rather than by adding a catch-all field.

**D6 — `ChapterSpec` dataclass instead of `ChapterBuilder` abstract
class.** An abstract `ChapterBuilder` with a `gather()` method was the
initial design. It was replaced by a plain `ChapterSpec` dataclass for
three reasons. First, the gather step doesn't need deferral — chapter
content comes from calculation results that exist before the report run
starts, not from the output of earlier LLM calls, so lazy evaluation via
a method adds complexity without benefit. Second, collapsing
`ChapterBuilder` (role + title) and `ChapterContent` (pointer_groups +
elements), which were effectively one record split across a class and its
return type, into a single flat dataclass is a genuine simplification:
fewer types, no inheritance, no abstract method protocol to satisfy.
Third, fail-fast behaviour improves: because all `ChapterSpec`s are built
before `chapter_generators` is called, a missing calculation result or
malformed table surfaces before any LLM call is made, rather than
partway through a multi-chapter run. The reusability that `ChapterBuilder`
subclasses provided is retained through plain builder functions
(see Section 10).

**D7 — The output contract is explicit: one header, and one placeholder
token per element.** The shared prompt instructs the model to do two
things the downstream pipeline depends on. First, open the chapter with
`# {number}. {title}` — this closes a previously implicit assumption the
parser relied on without enforcing. Second, for every `ReportElement`
passed in, emit its token on its own line at the point in the prose where
that figure or table should appear.

Placeholder tokens take the fixed forms `<<FIG:1>>` and `<<TBL:3>>`.
The type prefix (`FIG`/`TBL`) is language-independent Forelius
infrastructure — it is never a Dutch or English word. The number is the
one assigned by `ElementRegistry`. This means the token the LLM emits is
always the same shape regardless of report language, and `parse_section`
can find it with a single fixed regex — `re.fullmatch(r'<<(FIG|TBL):\d+>>',
line.strip())` — with no dependency on `ReportConfig` at all. The
human-readable rendered label (`Figuur 1`, `Figure 1`, `Abbildung 1`) is
derived by the renderer from the token number and `ReportConfig.figure_label`
or `ReportConfig.table_label`; it is never part of the token itself.

Using a format the LLM has no prior associations with in natural prose
reduces the risk of the model mangling, inlining, or stylistically varying
the token. `[Figuur 1]` resembles citation markers and editorial notes the
model has seen extensively in training; `<<FIG:1>>` does not.

The placeholder mechanism works as a three-step pipeline:

1. **Prompt → token in text.** The model receives `ReportElement` objects
   (e.g. `token: "<<TBL:3>>", description: "Soil parameters"`) and is
   told to place `<<TBL:3>>` on its own line at the appropriate point in
   the prose — not to describe or render the table itself, only to mark
   where it belongs.
2. **Token → position mapping.** `parse_section` scans the returned text
   for lines matching `re.fullmatch(r'<<(FIG|TBL):\d+>>', line.strip())`,
   identifies which line each token falls on, and builds a
   `line_element_map: dict[int, Plot | Table]` that associates text line
   numbers with the actual Python objects the caller originally provided
   in `ChapterSpec.elements`.
3. **Position → substitution.** The `ReportRenderer` walks the `Section`'s
   text lines in order; when it reaches a line number in `line_element_map`,
   it renders the associated `Plot` or `Table` object (as a LaTeX figure,
   a Markdown image link, or whatever the renderer produces) in place of
   the token line, using `ReportConfig.figure_label`/`table_label` to
   compose the rendered caption.

`_validate_all_elements_found` (see Section 11) guards the boundary
between steps 1 and 2: if the model omits a token, the error is surfaced
before rendering rather than silently producing a document with a missing
figure.

**D8 — Every chapter type has the same `elements` field.** The original
schema's omission of `elements` from the Conclusion input wasn't a
deliberate constraint so much as an unexamined default. Forelius gives
every chapter the same shape; if a particular report type wants to forbid
the Conclusion from introducing new figures, that's a calling convention,
not a schema rule.

**D9 — Elements are pre-registered across all chapters before any
generation begins.** The `ElementRegistry` is report-level (numbers must
be sequential across all chapters) but is passed as a dependency into each
`ChapterGenerator`. `chapter_generators` registers every element from every
spec in one upfront pass before yielding any generators. This means element
numbering is fully stable before any LLM call fires, which is a stronger
guarantee than the previous lazy per-chapter registration. The registry
is designed to be idempotent: calling `register_all` for the same elements
on a revision attempt (via `ChapterDraft.revise`) returns the same numbers
without incrementing the global counter.

**D10 — Rendering is behind a `ReportRenderer` interface.** The original
implementation generated a PDF via `pylatex` directly inside the
report-building step. Forelius separates "produce a parsed `Section` per
chapter" (format-agnostic) from "turn a list of `Section`s into an output
document" (format-specific), with LaTeX as the first concrete
implementation, leaving room for Markdown/Word/HTML renderers later
without touching chapter generation.

**D11 — `ChapterGenerator` as the single-chapter unit of
responsibility.** Generation logic (`_dispatch`, element resolution,
`ChapterInput` assembly, `parse_section`) lives on `ChapterGenerator`,
not on a report-level orchestrator. This gives `ChapterGenerator` a
single, coherent job — own everything needed to generate one chapter —
and makes it independently constructible and testable without a full
report setup. It is the natural home for `draft()`, since drafting is a
per-chapter concern.

**D12 — `ChapterDraft` depends only on `ChapterGenerator`, not on any
report-level object.** An earlier design placed `draft_chapter()` on
`ReportGenerator`, which forced `ChapterDraft` to hold a reference to the
full report orchestrator just to reach generation logic. Giving
`ChapterGenerator` sole ownership of generation logic means `ChapterDraft`
depends only on `ChapterGenerator`. The cohesion between `ChapterDraft`
and its collaborator matches the scope of what drafting actually involves.

**D13 — `chapter_generators` is the core primitive; `generate_report` is
a convenience wrapper.** Exposing `ChapterGenerator` instances to the
caller via a generator function is what makes `ChapterDraft` reachable in
practice — a purely internal construction (as in an earlier design where
generators were created and immediately consumed inside a function) would
leave `ChapterDraft` defined but unreachable. `generate_report` exists
because the batch case is common enough to deserve a one-liner, but it is
explicitly a thin wrapper: `return [gen.generate() for gen in
chapter_generators(config, specs)]`. If a future requirement introduces
report-level state between chapters (e.g. a Conclusion that reads earlier
`Section` objects for synthesis), `chapter_generators` can accommodate
that in the caller's loop without changing any API.

## 7. Package Layout

```
forelius/
├── baml_src/
│   ├── clients.baml
│   └── report/
│       ├── shared.baml         # ReportConfig, ChapterRef, PointerGroup,
│       │                       # ReportElement, ChapterInput, ChapterPromptCore
│       ├── introduction.baml   # ReportIntroduction
│       ├── chapter.baml        # ReportChapter
│       └── conclusion.baml     # ReportConclusion
├── baml_client/                # generated client
├── forelius/
│   ├── __init__.py
│   ├── config.py               # ReportConfig, ChapterRef, PointerGroup
│   ├── elements.py             # ReportElement, Plot, Table, ElementRegistry
│   ├── chapter.py              # ChapterRole, ChapterSpec (incl. with_feedback)
│   ├── generator.py            # ChapterGenerator, ChapterDraft,
│   │                           # chapter_generators, generate_report
│   ├── section.py              # Section, SubSection, parse_section
│   └── render/
│       ├── base.py             # ReportRenderer (Protocol)
│       └── latex.py            # LatexRenderer
└── tests/
```

## 8. Class & Function Reference

### BAML layer

```
class ChapterRef {
  number int
  title  string
}

class ReportConfig {
  discipline   string
  subject      string
  language     string
  figure_label string
  table_label  string
  outline      ChapterRef[]
}

class PointerGroup {
  heading string?
  items   string[]
}

class ReportElement {
  token       string   // placeholder the LLM emits, e.g. "<<FIG:1>>", "<<TBL:3>>"
  description string   // caption text, e.g. "Soil parameters"
}

class ChapterInput {
  report_config  ReportConfig
  chapter        ChapterRef
  pointer_groups PointerGroup[]
  elements       ReportElement[]
}

template_string ChapterPromptCore(input: ChapterInput, role_framing: string) #"
  You are a {{ input.report_config.discipline }} writing a report on
  {{ input.report_config.subject }}.
  Report structure:
  {% for c in input.report_config.outline %}{{ c.number }}. {{ c.title }}
  {% endfor %}
  {{ role_framing }}
  You should only write chapter {{ input.chapter.number }},
  "{{ input.chapter.title }}".
  Be factual, only report what is given as input. Do not explain terminology.
  Do not create markdown tables, they are inserted separately.
  For every figure or table provided, place its token on its own line at
  the point in the prose where that element should appear. Figures use the
  token `<<FIG:X>>` and tables use `<<TBL:X>>`, where X is the number given.
  Do not describe or render the element itself — only place the token.
  Every element provided must have exactly one token in the text.
  Start the chapter with: `# {{ input.chapter.number }}. {{ input.chapter.title }}`.
  Write the report in {{ input.report_config.language }}.
"#

function ReportIntroduction(input: ChapterInput) -> string {
  prompt #"
    {{ ChapterPromptCore(input, "Opening chapter — set scope, don't pre-empt results.") }}
    ...
  "#
}

function ReportChapter(input: ChapterInput) -> string {
  prompt #"
    {{ ChapterPromptCore(input, "") }}
    ...
  "#
}

function ReportConclusion(input: ChapterInput) -> string {
  prompt #"
    {{ ChapterPromptCore(input, "Closing chapter — synthesize earlier chapters, introduce nothing new.") }}
    ...
  "#
}
```

### Python layer

```python
class ChapterRole(Enum): INTRODUCTION, BODY, CONCLUSION

@dataclass
class ChapterSpec:
    role:           ChapterRole
    title:          str
    pointer_groups: list[PointerGroup]
    elements:       list[Plot | Table]   # raw, not yet numbered

    def with_feedback(self, feedback: str) -> ChapterSpec:
        """Return a copy of this spec with the feedback appended as a new PointerGroup."""
        return ChapterSpec(
            role=self.role,
            title=self.title,
            pointer_groups=self.pointer_groups + [PointerGroup(heading="Feedback", items=[feedback])],
            elements=self.elements,
        )


class ElementRegistry:
    def register_all(self, items: list[Plot | Table]) -> None: ...
    def resolve(self, items: list[Plot | Table]) -> list[ReportElement]: ...
    # register_all is idempotent: re-registering already-known elements
    # returns the same numbers without advancing the counter.


def parse_section(text: str, elements: list[Plot | Table]) -> Section:
    # Parses the LLM's returned text into a Section.
    # Scans for token lines matching re.fullmatch(r'<<(FIG|TBL):\d+>>', line.strip()),
    # builds a line_element_map associating each token's line number with the
    # corresponding Plot or Table object from elements.
    # Raises if any element in elements has no matching token in text
    # (_validate_all_elements_found), surfacing omissions before rendering.


@dataclass
class ChapterGenerator:
    config:   ReportConfig
    chapter:  ChapterRef
    spec:     ChapterSpec
    registry: ElementRegistry            # shared across all chapters in a report

    def generate(self) -> Section:
        elements = self.registry.resolve(self.spec.elements)
        chapter_input = ChapterInput(
            report_config=self.config,
            chapter=self.chapter,
            pointer_groups=self.spec.pointer_groups,
            elements=elements,
        )
        text = self._dispatch(self.spec.role, chapter_input)
        return parse_section(text, self.spec.elements)

    def draft(self) -> ChapterDraft:
        return ChapterDraft(self)

    def _dispatch(self, role: ChapterRole, chapter_input: ChapterInput) -> str:
        match role:
            case ChapterRole.INTRODUCTION: return b.ReportIntroduction(chapter_input)
            case ChapterRole.BODY:         return b.ReportChapter(chapter_input)
            case ChapterRole.CONCLUSION:   return b.ReportConclusion(chapter_input)


class ChapterDraft:
    def __init__(self, generator: ChapterGenerator):
        self._gen     = generator
        self._spec    = generator.spec
        self._section = generator.generate()   # eager first attempt

    def current(self) -> Section:
        return self._section

    def revise(self, feedback: str) -> Section:
        self._spec = self._spec.with_feedback(feedback)
        updated = ChapterGenerator(
            self._gen.config, self._gen.chapter, self._spec, self._gen.registry
        )
        self._section = updated.generate()
        return self._section

    def accept(self) -> Section:
        return self._section


def chapter_generators(
    config: ReportConfig,
    specs: list[ChapterSpec],
) -> Generator[ChapterGenerator, None, None]:
    config.outline = [ChapterRef(i + 1, s.title) for i, s in enumerate(specs)]
    registry = ElementRegistry(config)
    for spec in specs:                              # pre-register all elements upfront
        registry.register_all(spec.elements)
    for i, spec in enumerate(specs, start=1):
        yield ChapterGenerator(config, ChapterRef(i, spec.title), spec, registry)


def generate_report(config: ReportConfig, specs: list[ChapterSpec]) -> list[Section]:
    return [gen.generate() for gen in chapter_generators(config, specs)]


class ReportRenderer(Protocol):
    def render(self, sections: list[Section]) -> Any: ...

class LatexRenderer(ReportRenderer):
    def render(self, sections: list[Section]) -> Document: ...
```

## 9. Callflow

**Batch path** (all chapters generated without interaction):

1. The caller builds one `ReportConfig` and an ordered list of `ChapterSpec`s
   using plain builder functions.
2. `generate_report` delegates to `chapter_generators`, which derives the
   outline, creates the `ElementRegistry`, pre-registers all elements across
   all specs, then yields one `ChapterGenerator` per chapter.
3. Each `ChapterGenerator.generate()` resolves its elements, assembles a
   `ChapterInput`, dispatches to the correct BAML function by role, and
   parses the returned text into a `Section`.
4. The completed list of `Section`s is passed to a `ReportRenderer`.

**Interactive path** (one or more chapters reviewed and revised before
accepting):

1–2. Same as above, but the caller iterates `chapter_generators` directly
   instead of calling `generate_report`.
3. For chapters requiring review, the caller calls `gen.draft()` instead
   of `gen.generate()`. This returns a `ChapterDraft` and immediately
   performs the first generation attempt.
4. The caller inspects `draft.current()`, optionally calls
   `draft.revise(feedback)` one or more times (each call regenerates the
   chapter with the feedback appended as a new `PointerGroup`), then calls
   `draft.accept()` to obtain the final `Section`.
5. For chapters not requiring review, the caller calls `gen.generate()`
   directly.
6. All accepted `Section`s are collected and passed to a `ReportRenderer`.

## 10. Example: Implementing a Discipline

Domain-specific code constructs `ChapterSpec` instances through named
builder functions. A geotechnical Assumptions chapter:

```python
def assumptions_chapter(params: list[PileFoundationParams]) -> ChapterSpec:
    return ChapterSpec(
        role=ChapterRole.BODY,
        title="Uitgangspunten",
        pointer_groups=[
            PointerGroup(heading=None, items=[
                "load: SLS 100, ULS 1500",
                "Waterlevels: 0.1, 0.3, 1.2, -0.3, 0.5, based on piezometer XXXX",
                "Soil parameters are listed in the table; refer to the table, "
                "do not enumerate them individually.",
            ]),
        ],
        elements=[build_params_table(params)],
    )
```

**Batch report generation:**

```python
config = ReportConfig(
    discipline="geotechnical engineer",
    subject="a pile foundation calculation",
    language="Dutch",
    figure_label="Figuur",
    table_label="Tabel",
    outline=[],   # derived automatically by chapter_generators
)

specs = [
    introduction_chapter(work_order),
    soil_investigation_chapter(cpts),
    assumptions_chapter(params),
    modelling_chapter(pile_type, skin_friction_ranges),
    results_chapter(pile_results),
    conclusion_chapter(pile_type, pile_tip_level),
]

sections = generate_report(config, specs)
LatexRenderer().render(sections)
```

**Interactive report generation (same infrastructure, caller drives the
loop):**

```python
sections = []
for gen in chapter_generators(config, specs):
    draft = gen.draft()
    print(draft.current().text)
    feedback = input("Feedback (or enter to accept): ")
    while feedback:
        draft.revise(feedback)
        print(draft.current().text)
        feedback = input("Feedback (or enter to accept): ")
    sections.append(draft.accept())

LatexRenderer().render(sections)
```

## 11. Open Questions / Future Work

- Whether `ReportConclusion` should eventually return structured output
  (e.g. `{summary, recommendations}`) rather than free text, now that its
  signature is independent of the other two functions.
- Whether `ChapterGenerator` should support a per-chapter LLM client
  override (e.g. a stronger model for Conclusion's synthesis, a cheaper
  one for boilerplate chapters).
- Validation parity with the original implementation's
  `_validate_all_elements_found` check — confirming every `ReportElement`
  passed into a chapter actually appears as a marker in the returned text,
  and surfacing a clear error before rendering if not.
- Test coverage across at least two disciplines per chapter role, to
  catch any residual assumptions that crept back in from the geotechnical
  origin of this design.
- Whether `PointerGroup` needs a nesting level (sub-bullets) for chapters
  with deeper structure than a flat list supports.
- If a future requirement introduces chapter-to-chapter dependencies
  (e.g. a Conclusion that reads earlier `Section` objects for synthesis),
  `chapter_generators` can accommodate that in the caller's loop, but
  `generate_report` would need to become stateful and should at that
  point be promoted to a class.

## 12. Appendix: Mapping from the Original Implementation

| Original (geotechnical-only) | Forelius equivalent |
|---|---|
| `FoundationDesignIntroductionReporter` | `ReportIntroduction` |
| `FoundationDesignSoilInvestigationReporter` | `ReportChapter` |
| `FoundationDesignAssumptionsReporter` | `ReportChapter` |
| `FoundationDesignModellingReporter` | `ReportChapter` |
| `FoundationDesignResultsReporter` | `ReportChapter` |
| `FoundationDesignConclusionReporter` | `ReportConclusion` |
| `ReportBaseLine*` / `ModellingPointers` / `ResultPointers` | `ChapterSpec` + `PointerGroup[]` |
| `ChapterBuilder` + `ChapterContent` | `ChapterSpec` (single dataclass) |
| `ReportGenerator` (class) | `ChapterGenerator` + `chapter_generators` + `generate_report` |
| `ReportGenerator.draft_chapter()` | `ChapterGenerator.draft()` → `ChapterDraft` |
| `ReportElement` | `ReportElement` (unchanged) |
| `CaptionNumbers` | `ElementRegistry` |
| `_llm_text_generation_router` (isinstance dispatch) | `ChapterGenerator._dispatch` (role enum match) |
| Hardcoded Dutch TOC + chapter number in each prompt | `ReportConfig.outline` + `ChapterRef` |
