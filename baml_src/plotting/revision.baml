function ReviseXYPlotIntent(input: ReviseXYPlotIntentInput) -> XYPlotIntent {
  client ForeliusClaudeHaiku45
  prompt #"
    Revise the current XY plot intent using the user's feedback.

    Current intent:
    {{ input.current_intent }}

    User feedback:
    {{ input.feedback }}

    {{ PlotDatasetMetadataPrompt(input.dataset) }}

    Revision rules:
    - Revise only the plot intent; do not revise or invent data.
    - Preserve current settings unless the feedback asks to change them.
    - Choose x and y only from the provided dataset column names.
    - Do not invent columns, rows, values, calculations, or data transformations.
    - Do not generate code.

    {{ XYPlotIntentContract() }}
  "#
}

test revise_xy_plot_intent_points_only {
  functions [ReviseXYPlotIntent]
  args {
    input {
      current_intent {
        x "displacement"
        y "force"
        caption "Force versus displacement."
        options {
          title "Force-displacement"
          x_label "Displacement (mm)"
          y_label "Force (kN)"
          x_lim null
          y_lim null
          grid MAJOR
          line_style SOLID
          marker NONE
          color null
          invert_x false
          invert_y false
        }
      }
      feedback "Maak er alleen punten van."
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

test revise_xy_plot_intent_invert_depth_axis {
  functions [ReviseXYPlotIntent]
  args {
    input {
      current_intent {
        x "Zetting"
        y "Diepte"
        caption "Zetting tegen diepte."
        options {
          title "Zetting tegen diepte"
          x_label "Zetting (mm)"
          y_label "Diepte (m)"
          x_lim null
          y_lim null
          grid MAJOR
          line_style SOLID
          marker CIRCLE
          color null
          invert_x false
          invert_y false
        }
      }
      feedback "Keer de diepte-as om zodat diepte naar beneden loopt."
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

test revise_xy_plot_intent_axis_minimum_zero {
  functions [ReviseXYPlotIntent]
  args {
    input {
      current_intent {
        x "Diepte"
        y "Zetting"
        caption "Zetting als functie van diepte."
        options {
          title "Zetting tegen Diepte"
          x_label "Diepte (m)"
          y_label "Zetting (mm)"
          x_lim null
          y_lim null
          grid MAJOR
          line_style SOLID
          marker CIRCLE
          color null
          invert_x false
          invert_y false
        }
      }
      feedback "set the x and y axis to a minimum value of 0"
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
        assumptions []
      }
    }
  }
}
