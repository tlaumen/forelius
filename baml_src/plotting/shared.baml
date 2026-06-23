enum ExtractionConfidence {
  LOW
  MEDIUM
  HIGH
}

enum ExtractedDataType {
  NUMBER
  TEXT
  CATEGORY
  DATE
}

enum PlotGrid {
  NONE
  MAJOR
  BOTH
}

enum PlotLineStyle {
  SOLID
  DASHED
  DOTTED
  DASHDOT
  NONE
}

enum PlotMarker {
  NONE
  CIRCLE
  SQUARE
  TRIANGLE
  DIAMOND
  CROSS
}

class ExtractedColumn {
  name string
  unit string?
  data_type ExtractedDataType
  values string[]
}

class ExtractedDataset {
  data_start_line int
  data_end_line int
  columns ExtractedColumn[]
  confidence ExtractionConfidence
  assumptions string[]
}

class DatasetColumnMetadata {
  name string
  unit string?
  data_type ExtractedDataType
}

class DatasetMetadata {
  columns DatasetColumnMetadata[]
  assumptions string[]
}

class AxisLimit {
  min float?
  max float?
}

class XYPlotOptions {
  title string?
  x_label string?
  y_label string?
  x_lim AxisLimit?
  y_lim AxisLimit?
  grid PlotGrid
  line_style PlotLineStyle
  marker PlotMarker
  color string?
  invert_x bool
  invert_y bool
}

class XYPlotIntent {
  x string
  y string
  caption string
  options XYPlotOptions
}

class CreateXYPlotIntentInput {
  request string
  dataset DatasetMetadata
}

class ReviseXYPlotIntentInput {
  current_intent XYPlotIntent
  feedback string
  dataset DatasetMetadata
}

template_string PlotDatasetMetadataPrompt(dataset: DatasetMetadata) #"
Dataset columns available for plotting:
{% for column in dataset.columns %}
- Name: {{ column.name }}
  Unit: {{ column.unit }}
  Data type: {{ column.data_type }}
{% endfor %}

Assumptions from extraction:
{% for assumption in dataset.assumptions %}
- {{ assumption }}
{% endfor %}
"#

template_string XYPlotIntentContract() #"
Output contract:
- Choose x and y only from the provided dataset column names.
- Choose only numeric columns for x and y.
- Do not invent columns, rows, values, calculations, or data transformations.
- Create a single XY plot intent only; no bar charts, grouped plots, subplots, or multi-series plots.
- Use only supported enum values for grid, line_style, and marker.
- If the request does not specify style, prefer grid MAJOR, line_style SOLID, and marker NONE.
- If line_style is NONE, marker must not be NONE.
- If marker is NONE, line_style must not be NONE.
- Keep title, x_label, and y_label concise.
- Keep caption technically clear and no longer than one sentence.
- Do not generate code.

{{ ctx.output_format }}
"#
