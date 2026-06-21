function ReportConclusion(input: ChapterInput) -> string {
  client ForeliusClaudeHaiku45
  prompt #"
    {{ SharedReportPromptCore(input) }}

    Conclusion-specific instructions:
    - Synthesize only from the supplied pointers.
    - Do not introduce new facts, assumptions, calculations, or recommendations.
    - State the conclusion clearly and keep it proportional to the available context.

    {{ ctx.output_format }}
  "#
}

test conclusion_summary {
  functions [ReportConclusion]
  args {
    input {
      config {
        discipline "geotechnical engineer"
        subject "pile foundation calculation"
        language "English"
        figure_label "Figure"
        table_label "Table"
        outline [
          {
            number 1
            title "Introduction"
          }
          {
            number 2
            title "Results"
          }
          {
            number 3
            title "Conclusion"
          }
        ]
      }
      chapter {
        number 3
        title "Conclusion"
      }
      pointers [
        "The calculated settlements remain within the serviceability criterion."
        "The governing load case is documented in the results chapter."
      ]
      elements []
    }
  }
}

test conclusion_with_reference_element {
  functions [ReportConclusion]
  args {
    input {
      config {
        discipline "civil engineer"
        subject "retaining wall assessment"
        language "English"
        figure_label "Figure"
        table_label "Table"
        outline [
          {
            number 1
            title "Introduction"
          }
          {
            number 2
            title "Assessment"
          }
          {
            number 3
            title "Conclusion"
          }
        ]
      }
      chapter {
        number 3
        title "Conclusion"
      }
      pointers [
        "Conclude that the checked wall section satisfies the stated limit state."
        "Refer to the summary table if discussing the utilization result."
      ]
      elements [
        {
          element_id "tbl_0001"
          kind "table"
          caption "Utilization summary"
          placement_token "<<TBL:tbl_0001>>"
          reference_token "<<REF:tbl_0001>>"
        }
      ]
    }
  }
}
