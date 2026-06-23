# Forelius

Forelius is a package to help civil engineers write reports using LLM-assisted writing and templating with a simple Python API.

Forelius is named after Mr. Forel, who wrote about ants.

## Requirements

Forelius uses BAML with Anthropic Claude Haiku 4.5 for real chapter generation. Set the required API key before calling real generation:

```bash
export ANTHROPIC_API_KEY="..."
```

You can also place it in a local `.env` file; `initialize()` loads `.env` from the current working directory.

Normal tests do not make live LLM calls.

## Short example

```python
from forelius import (
    ChapterRole,
    ChapterSpec,
    GenerationOrder,
    MarkdownRenderer,
    ReportConfig,
    generate_report,
    initialize,
)

initialize()

config = ReportConfig(
    discipline="geotechnical engineer",
    subject="pile foundation calculation",
    language="English",
    figure_label="Figure",
    table_label="Table",
)

specs = [
    ChapterSpec(
        role=ChapterRole.INTRODUCTION,
        title="Introduction",
        pointers=["Explain the report purpose and scope."],
    ),
    ChapterSpec(
        role=ChapterRole.BODY,
        title="Results",
        pointers=["Discuss the governing calculation results."],
    ),
    ChapterSpec(
        role=ChapterRole.CONCLUSION,
        title="Conclusion",
        pointers=["Summarize the final engineering conclusion."],
    ),
]

sections = generate_report(
    config,
    specs,
    generation_order=GenerationOrder.INTRODUCTION_LAST,
)
markdown = MarkdownRenderer().render(config, sections)
```

## Plot generation example

Forelius can generate a safe PNG-backed `Plot` from freeform data and a natural-language plot request. The LLM extracts data and chooses a constrained plot intent; Forelius validates the result and renders with trusted matplotlib code.

```python
from pathlib import Path

from forelius import generate_plot_from_freeform, initialize

initialize()

plot = generate_plot_from_freeform(
    """
    Maak een grafiek van zetting tegen diepte.

    Diepte (m); Zetting (mm)
    0; 0
    1,5; 12,5
    2,0; -
    """,
    output_dir=Path("plots"),
    filename_stem="zetting_diepte",
)

print(plot.path)
```

The returned value is a normal `Plot` object with a saved PNG path, so it can be used in `ChapterSpec.elements` like any other figure.

For revision workflows, use the session API from `forelius.plotting`:

```python
from pathlib import Path

from forelius import initialize
from forelius.plotting import generate_plot_session

initialize()

session = generate_plot_session("Plot force versus displacement...", Path("plots"))
session = session.revise("Maak er alleen punten van.")
final_plot = session.plot
```

## Interactive example

For an easy guided flow, use the interactive report prompt. It asks for report settings, chapter titles, pointers, optional figures/tables, and lets you review or revise each generated chapter before rendering Markdown.

```python
from forelius import initialize, prompt_for_report

initialize()
markdown = prompt_for_report()
print(markdown)
```

Manual end-to-end scripts are included:

```bash
uv run e2e/manual_prompt_for_report.py
uv run e2e/manual_generate_plot.py
```

## BAML client generation

The generated BAML client lives in the top-level `baml_client/` directory. Regenerate it after changing files in `baml_src/`:

```bash
uv run baml-cli generate
```

Check BAML source files with:

```bash
uv run baml-cli check
```

## Tests

Run the offline test suite with:

```bash
uv run pytest
```
