function ReportIntroduction(input: ChapterInput) -> string {
  client ForeliusClaudeHaiku45
  prompt #"
    {{ SharedReportPromptCore(input) }}

    Introduction-specific instructions:
    - Establish the project context, report purpose, and chapter scope.
    - Do not pre-empt detailed results, calculations, or conclusions.
    - Do not introduce facts that are not present in the pointers.

    {{ ctx.output_format }}
  "#
}

test introduction_context_scope {
  functions [ReportIntroduction]
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
            title "Design basis"
          }
          {
            number 3
            title "Conclusion"
          }
        ]
      }
      chapter {
        number 1
        title "Introduction"
      }
      pointers [
        "Explain the purpose of the calculation report."
        "Mention that the report covers pile foundation design assumptions."
      ]
      elements []
    }
  }
}

test introduction_with_project_constraints {
  functions [ReportIntroduction]
  args {
    input {
      config {
        discipline "civil engineer"
        subject "retaining wall assessment"
        language "Dutch"
        figure_label "Figuur"
        table_label "Tabel"
        outline [
          {
            number 1
            title "Inleiding"
          }
          {
            number 2
            title "Uitgangspunten"
          }
        ]
      }
      chapter {
        number 1
        title "Inleiding"
      }
      pointers [
        "Beschrijf de aanleiding van de beoordeling."
        "Benoem dat resultaten later in het rapport worden behandeld."
      ]
      elements []
    }
  }
}
