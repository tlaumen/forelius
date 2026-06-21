class ChapterRef {
  number int
  title string
}

class ReportConfig {
  discipline string
  subject string
  language string
  figure_label string
  table_label string
  outline ChapterRef[]
}

class ReportElement {
  element_id string
  kind string
  caption string
  placement_token string
  reference_token string
}

class ChapterInput {
  config ReportConfig
  chapter ChapterRef
  pointers string[]
  elements ReportElement[]
}

template_string SharedReportPromptCore(input: ChapterInput) #"
You are writing a civil-engineering report chapter.

Report context:
- Discipline: {{ input.config.discipline }}
- Subject: {{ input.config.subject }}
- Language: {{ input.config.language }}

Final report outline:
{% for chapter in input.config.outline %}
- {{ chapter.number }}. {{ chapter.title }}
{% endfor %}

Current chapter:
- Number: {{ input.chapter.number }}
- Title: {{ input.chapter.title }}

Chapter pointers:
{% for pointer in input.pointers %}
- {{ pointer }}
{% endfor %}

Available report elements:
{% for element in input.elements %}
- ID: {{ element.element_id }}
  Kind: {{ element.kind }}
  Caption: {{ element.caption }}
  Placement token: {{ element.placement_token }}
  Reference token: {{ element.reference_token }}
{% endfor %}

Output contract:
- Start with exactly one top-level Markdown chapter header using '# '.
- Write only the current chapter.
- Use every provided placement token exactly once when the element should be inserted.
- Put placement tokens on their own line, with no surrounding prose.
- Use inline reference tokens such as <<REF:fig_0001>> or <<REF:tbl_0001>> when referring to figures or tables.
- Do not invent visible figure/table numbering.
- Do not write labels such as Figure 1 or Table 1 yourself.
- Do not render tables or figures yourself.
- Do not include Markdown image syntax for figures.
- Do not include Markdown table syntax for tables.
- Keep the writing concise and technically clear.
"#
