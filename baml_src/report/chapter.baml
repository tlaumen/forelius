function ReportChapter(input: ChapterInput) -> string {
  client ForeliusClaudeHaiku45
  prompt #"
    {{ SharedReportPromptCore(input) }}

    Body-chapter-specific instructions:
    - Develop the supplied pointers into a coherent technical chapter.
    - Stay discipline-agnostic and use only the provided context.
    - When discussing provided figures or tables, refer to them only with their inline reference tokens.

    {{ ctx.output_format }}
  "#
}

test chapter_with_figure_and_table {
  functions [ReportChapter]
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
        ]
      }
      chapter {
        number 2
        title "Results"
      }
      pointers [
        "Discuss the calculated settlements."
        "Describe the governing load case."
      ]
      elements [
        {
          element_id "fig_0001"
          kind "figure"
          caption "Calculated settlement profile"
          placement_token "<<FIG:fig_0001>>"
          reference_token "<<REF:fig_0001>>"
        }
        {
          element_id "tbl_0001"
          kind "table"
          caption "Governing load combinations"
          placement_token "<<TBL:tbl_0001>>"
          reference_token "<<REF:tbl_0001>>"
        }
      ]
    }
  }
}

test chapter_without_elements {
  functions [ReportChapter]
  args {
    input {
      config {
        discipline "structural engineer"
        subject "temporary works check"
        language "English"
        figure_label "Figure"
        table_label "Table"
        outline [
          {
            number 1
            title "Method"
          }
          {
            number 2
            title "Verification"
          }
        ]
      }
      chapter {
        number 2
        title "Verification"
      }
      pointers [
        "State the verification approach."
        "Explain that checks are based on the supplied design actions."
      ]
      elements []
    }
  }
}
