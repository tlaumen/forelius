# Plot Generation Plan

## Goal

Add a seamless, safe plotting workflow to Forelius.

The user should be able to provide messy/freeform data and a natural-language request such as:

```text
Maak een last-zakkingsdiagram met markers.

Belasting kN    Zetting mm
100             4,1
200             8,3
300             12,9
```

Forelius should extract the data, infer or create a simple plot intent, render a plot image with trusted internal code, and return a normal `Plot` element that can be used in a report.

## Core design

Use an LLM for **data extraction and plot intent**, but never for executable plotting code.

```text
User freeform data + plot request
      ↓
Forelius numbers the input lines
      ↓
LLM extracts a column-oriented dataset
      ↓
Forelius validates the extracted dataset
      ↓
LLM/Forelius creates a simple XY plot intent
      ↓
Forelius validates the plot intent against the dataset
      ↓
Forelius renders with trusted matplotlib code
      ↓
Forelius returns Plot(...)
      ↓
Optional user revision loop updates the plot intent only
```

## Rationale

### Why not run LLM-generated Python?

Running LLM-generated Python on a user's machine is risky. Even with sandboxing, arbitrary code can attempt to access files, environment variables, network resources, or system APIs.

Forelius only needs to create a plot image. Therefore, arbitrary code execution is unnecessary.

Decision:

```text
LLM may produce structured data and settings.
Forelius executes only trusted internal plotting code.
```

### Why not require CSV or a `Table` input?

If users already have clean CSV data, creating a plot in Excel is often easy. Forelius becomes more valuable if it accepts messy/freeform data directly, for example:

- copied Excel ranges;
- rough text tables;
- Markdown tables;
- semicolon-separated Dutch data;
- narrative data snippets;
- data pasted together with explanatory text.

Decision:

```text
The starting point is freeform user-provided data, not a strict table model.
```

### Why LLM-only extraction for v1?

A deterministic parser for all likely input formats would be complex and still incomplete. A hybrid deterministic-plus-LLM parser may be more robust later, but it is more work.

For v1, the simplest seamless implementation is:

```text
Use the LLM to extract data from freeform input.
Validate the result strictly in Python.
```

This keeps implementation smaller while preserving safety through validation.

### Why column-oriented extraction?

Plotting is naturally column-based: choose one column for x, one column for y.

Instead of separating `columns` and `rows`, the LLM should return each column with its values:

```json
{
  "columns": [
    {
      "name": "Belasting",
      "unit": "kN",
      "data_type": "number",
      "values": ["100", "200", "300"]
    },
    {
      "name": "Zetting",
      "unit": "mm",
      "data_type": "number",
      "values": ["4,1", "8,3", "12,9"]
    }
  ]
}
```

This makes it easy to:

- choose x/y columns;
- validate data types per column;
- parse numeric values column by column;
- derive axis labels from names and units;
- support future grouped/multi-series plots.

Decision:

```text
Use column-oriented extracted datasets.
```

### Why only a normal XY plot in v1?

A normal XY plot can cover both line and scatter plots:

- line plot: line style is set, marker may be absent;
- scatter plot: line style is `none`, marker is set;
- line with markers: both line style and marker are set.

This avoids introducing multiple plot types too early.

Decision:

```text
V1 supports one XY plot only.
Multiple plots, grouped plots, bar charts, and subplots can come later.
```

## User experience

### Initial request

User provides data and intent together:

```text
Maak een last-zakkingsdiagram met markers.

Belasting kN    Zetting mm
100             4,1
200             8,3
300             12,9
```

### Generated result

Forelius renders a first draft plot and summarizes what happened:

```text
Grafiek gemaakt.

Gebruikte data:
- Regels: 3 t/m 6
- X-as: Belasting [kN]
- Y-as: Zetting [mm]
- Datapunten: 3
- Aannames: decimale komma's geïnterpreteerd als punten.

Wil je iets aanpassen?
```

The plot is returned as a normal `Plot` element.

### Revision examples

The user can revise the plot using natural language:

```text
Maak er alleen punten van.
```

```text
Zet de y-as van 0 tot 15.
```

```text
Gebruik een gestippelde lijn en geen markers.
```

Important: revisions update only the plot intent. The extracted dataset is reused unless the user provides new data.

## Line numbering

Before sending user input to the LLM, Forelius should number lines:

```text
1: Maak een last-zakkingsdiagram met markers.
2:
3: Belasting kN    Zetting mm
4: 100             4,1
5: 200             8,3
6: 300             12,9
```

The LLM must return where the data starts and ends:

```json
{
  "data_start_line": 3,
  "data_end_line": 6
}
```

Rationale:

- makes extracted data auditable;
- helps user understand what was used;
- supports future correction workflows;
- helps catch hallucinated extraction.

## Data extraction model

Proposed model:

```python
from typing import Literal
from pydantic import BaseModel, Field


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
```

### Notes

- Values should initially remain strings.
- Forelius parses numeric values itself.
- This allows support for decimal commas and stricter validation.
- Data types are intentionally limited.

## Extraction BAML function

Conceptual BAML function:

```text
ExtractDatasetFromFreeform(numbered_input: string) -> ExtractedDataset
```

Prompt requirements:

```text
Extract tabular or plot-ready data from the user's input.

Rules:
- Return only data explicitly present in the input.
- Do not invent rows or values.
- Use column-oriented output.
- Include data_start_line and data_end_line.
- Preserve original value strings where possible.
- Identify units when present.
- Assign data_type as number, text, category, or date.
- Convert no values in the explanation; Forelius will parse numbers.
- Mention assumptions, such as decimal commas.
- If extraction is uncertain, set confidence to low or medium.
```

## Dataset validation

Forelius must validate every extracted dataset before plotting.

Required checks:

```text
- data_start_line >= 1
- data_end_line >= data_start_line
- at least 2 columns
- all column names are non-empty
- column names are unique or made unique deterministically
- all columns have the same number of values
- every column has at least 2 values
- confidence is present
- numeric columns can be parsed as finite floats
```

Numeric parsing should support:

```text
4.1
4,1
1,234.56
1.234,56
```

NaN and Infinity must be rejected.

## Plot intent model

V1 supports a single normal XY plot.

```python
class XYPlotOptions(BaseModel):
    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None

    x_lim: tuple[float, float] | None = None
    y_lim: tuple[float, float] | None = None

    x_tick_spacing: float | None = None
    y_tick_spacing: float | None = None
    number_format: Literal["auto", "integer", "1_decimal", "2_decimals"] = "auto"

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

### Rationale for options

The options are limited but cover common user needs:

- axis labels;
- plot title;
- axis limits;
- tick spacing;
- grid;
- line/scatter appearance;
- inverted axes for profile-like plots.

They intentionally do not expose arbitrary matplotlib kwargs.

## Plot intent creation

There are two possible approaches.

### Option A: LLM creates full `XYPlotIntent`

The LLM receives:

- the user's plot request;
- extracted column metadata;
- maybe a small preview of values.

It returns:

```json
{
  "x": "Belasting",
  "y": "Zetting",
  "caption": "Last-zakkingsdiagram met belasting op de x-as en zetting op de y-as.",
  "options": {
    "title": "Zetting versus belasting",
    "x_label": "Belasting [kN]",
    "y_label": "Zetting [mm]",
    "line_style": "solid",
    "marker": "circle",
    "grid": "major"
  }
}
```

### Option B: Forelius chooses defaults and LLM fills text/style

Forelius can default to:

```text
first numeric column -> x
second numeric column -> y
```

Then the LLM only decides title, caption, and style.

Recommendation for v1:

```text
Use Option A initially for seamless natural-language behavior.
Keep validation strict so invalid x/y choices fail safely.
```

## Plot intent validation

Before rendering, validate:

```text
- x column exists
- y column exists
- x column has data_type number
- y column has data_type number
- x and y have equal value counts
- line_style and marker are not both none
- x_lim and y_lim are increasing when present
- tick spacing is positive when present
- title, labels, and caption have reasonable lengths
```

## Rendering

Rendering is trusted internal code using matplotlib.

Use a non-interactive backend:

```python
import matplotlib
matplotlib.use("Agg")
```

Line/marker mappings:

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

Renderer shape:

```python
def render_xy_plot(
    dataset: ExtractedDataset,
    intent: XYPlotIntent,
    output_dir: Path,
    filename_stem: str | None = None,
) -> Plot:
    ...
```

Behavior:

1. Resolve x/y columns.
2. Parse numeric values.
3. Create output directory.
4. Generate a safe filename if needed.
5. Render with `ax.plot(...)`.
6. Apply labels, limits, ticks, grid, and inversion.
7. Save image as PNG.
8. Close the figure.
9. Return `Plot(caption=intent.caption, path=output_path)`.

## Optional revision loop

After rendering, the user may request changes.

Conceptual BAML function:

```text
ReviseXYPlotIntent(
    current_intent: XYPlotIntent,
    extracted_dataset: ExtractedDataset,
    user_revision: string,
) -> XYPlotIntent
```

Rules:

```text
- Preserve dataset and column values.
- Only change the plot intent.
- Do not invent new columns.
- Keep x/y numeric.
- Preserve unspecified settings.
```

Examples:

```text
User: Maak er alleen punten van.
Change: line_style = "none", marker = "circle"
```

```text
User: Zet de y-as van 0 tot 15.
Change: y_lim = (0, 15)
```

## Suggested package structure

```text
forelius/plotting/__init__.py
forelius/plotting/data.py
forelius/plotting/intent.py
forelius/plotting/render.py
```

Responsibilities:

```text
data.py
  ExtractedColumn
  ExtractedDataset
  number_input_lines
  parse_numeric_value
  validate_extracted_dataset

intent.py
  XYPlotOptions
  XYPlotIntent
  validate_plot_intent

render.py
  render_xy_plot
```

BAML additions:

```text
ExtractDatasetFromFreeform
CreateXYPlotIntent
ReviseXYPlotIntent
```

## Integration with existing report elements

The renderer returns a normal `Plot`:

```python
plot = render_xy_plot(dataset, intent, output_dir)
```

Then it can be added to a chapter like any other element:

```python
chapter = chapter.model_copy(update={
    "elements": [*chapter.elements, plot],
})
```

The existing rendering/generation behavior should not need major changes.

## Testing plan

### Unit tests

- Numbered input lines are generated correctly.
- `ExtractedDataset` validation accepts valid column-oriented data.
- Validation rejects unequal column lengths.
- Validation rejects fewer than two columns.
- Validation rejects fewer than two values.
- Numeric parser accepts decimal points.
- Numeric parser accepts decimal commas.
- Numeric parser accepts Dutch thousands format.
- Numeric parser rejects NaN/Infinity.
- Plot intent validation rejects missing x/y columns.
- Plot intent validation rejects non-numeric x/y columns.
- Plot intent validation rejects invisible plot: `line_style="none"` and `marker="none"`.
- Renderer writes a PNG to the requested output directory.
- Renderer closes figures after saving.

### Offline tests

Automated tests should not call live LLMs.

Mock BAML outputs for:

- dataset extraction;
- plot intent creation;
- plot intent revision.

### Manual/e2e tests

Add a manual script later, for example:

```text
e2e/manual_generate_plot.py
```

It can call real BAML functions and write the resulting plot image to a local output directory.

## Implementation phases

### Phase 1 — Models and renderer

- Add `ExtractedColumn` and `ExtractedDataset`.
- Add validation and numeric parsing.
- Add `XYPlotIntent` and `XYPlotOptions`.
- Add `render_xy_plot`.
- Add offline tests.

### Phase 2 — BAML extraction and intent

- Add `ExtractDatasetFromFreeform`.
- Add `CreateXYPlotIntent`.
- Add Python wrapper that does:

```text
number lines -> extract dataset -> validate -> create intent -> validate -> render
```

### Phase 3 — Revision loop

- Add `ReviseXYPlotIntent`.
- Re-render the same dataset with updated intent.
- Add manual flow for iterative changes.

### Phase 4 — Interactive report integration

- Add an interactive element option: `grafiek`.
- User pastes data and plot request.
- Forelius generates plot and adds it to chapter elements.

### Phase 5 — Future plot types

Only after v1 works well, consider:

- multiple series;
- grouped plots;
- bar plots;
- reference lines;
- profile/depth plots;
- subplots.

## Open questions

- Should low-confidence extraction still render a draft or ask for confirmation first?
- Should values remain strings in the model permanently, or should validated numeric columns cache parsed floats?
- Should output files be deterministic, UUID-based, or content-hash-based?
- Should plots be PNG only in v1?
- Should plot generation be available in the public API before interactive integration?
