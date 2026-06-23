function CreateXYPlotIntent(input: CreateXYPlotIntentInput) -> XYPlotIntent {
  client ForeliusClaudeHaiku45
  prompt #"
    Create a constrained XY plot intent for the user's request.

    User request:
    {{ input.request }}

    {{ PlotDatasetMetadataPrompt(input.dataset) }}

    {{ XYPlotIntentContract() }}
  "#
}

test create_xy_plot_intent_settlement_line {
  functions [CreateXYPlotIntent]
  args {
    input {
      request "Maak een grafiek van zetting tegen diepte."
      dataset {
        columns [
          {
            name "Diepte"
            unit "m"
            data_type NUMBER
          }
          {
            name "Zetting"
            unit "mm"
            data_type NUMBER
          }
        ]
        assumptions ["Decimal commas preserved from source."]
      }
    }
  }
}

test create_xy_plot_intent_points_only {
  functions [CreateXYPlotIntent]
  args {
    input {
      request "Show force versus displacement as points only."
      dataset {
        columns [
          {
            name "displacement"
            unit "mm"
            data_type NUMBER
          }
          {
            name "force"
            unit "kN"
            data_type NUMBER
          }
        ]
        assumptions []
      }
    }
  }
}
