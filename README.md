# Forelius

Forelius is a package to help civil engineers write reports using LLM-assisted writing and templating with a simple Python API.

Forelius is named after Mr. Forel, who wrote about ants.

## Requirements

Forelius uses BAML with Anthropic Claude Haiku 4.5 for real chapter generation. Set the required API key before calling real generation:

```bash
export ANTHROPIC_API_KEY="..."
```

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
