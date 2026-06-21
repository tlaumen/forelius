import re

from forelius.config import ReportConfig
from forelius.elements import ElementKind, Plot, ResolvedElement, Table
from forelius.section import REFERENCE_TOKEN_PATTERN, Section


class MarkdownRenderError(ValueError):
    pass


class MarkdownRenderer:
    def render(self, config: ReportConfig, sections: list[Section]) -> str:
        visible_labels = self._assign_visible_labels(config, sections)
        rendered_lines: list[str] = []

        for section in sections:
            for line_number, line in enumerate(section.text.splitlines()):
                if line_number in section.line_element_map:
                    rendered_lines.extend(
                        self._render_element(
                            config,
                            section.line_element_map[line_number],
                            visible_labels,
                        )
                    )
                else:
                    rendered_lines.append(self._replace_references(line, visible_labels))

        return "\n".join(rendered_lines)

    def _assign_visible_labels(
        self, config: ReportConfig, sections: list[Section]
    ) -> dict[str, str]:
        visible_labels: dict[str, str] = {}
        figure_count = 0
        table_count = 0

        for section in sections:
            for line_number in sorted(section.line_element_map):
                resolved = section.line_element_map[line_number]
                reference_token = resolved.report_element.reference_token
                if resolved.report_element.kind is ElementKind.FIGURE:
                    figure_count += 1
                    visible_labels[reference_token] = f"{config.figure_label} {figure_count}"
                else:
                    table_count += 1
                    visible_labels[reference_token] = f"{config.table_label} {table_count}"

        return visible_labels

    def _replace_references(self, line: str, visible_labels: dict[str, str]) -> str:
        def replace(match: re.Match[str]) -> str:
            token = match.group(0)
            if token not in visible_labels:
                raise MarkdownRenderError(f"Unknown reference token: {token}")
            return visible_labels[token]

        return REFERENCE_TOKEN_PATTERN.sub(replace, line)

    def _render_element(
        self,
        config: ReportConfig,
        resolved: ResolvedElement,
        visible_labels: dict[str, str],
    ) -> list[str]:
        if resolved.report_element.kind is ElementKind.FIGURE:
            return self._render_figure(config, resolved, visible_labels)
        return self._render_table(config, resolved, visible_labels)

    def _render_figure(
        self,
        config: ReportConfig,
        resolved: ResolvedElement,
        visible_labels: dict[str, str],
    ) -> list[str]:
        plot = resolved.original
        if not isinstance(plot, Plot):
            raise MarkdownRenderError("Resolved figure element does not contain a Plot")

        label = self._visible_label_for_element(resolved, visible_labels)
        return [
            f"![{plot.caption}]({plot.path})",
            "",
            f"**{label}: {plot.caption}**",
        ]

    def _render_table(
        self,
        config: ReportConfig,
        resolved: ResolvedElement,
        visible_labels: dict[str, str],
    ) -> list[str]:
        table = resolved.original
        if not isinstance(table, Table):
            raise MarkdownRenderError("Resolved table element does not contain a Table")

        label = self._visible_label_for_element(resolved, visible_labels)
        return [
            f"**{label}: {table.caption}**",
            "",
            self._render_table_row(table.headers),
            self._render_table_row(["---" for _ in table.headers]),
            *[self._render_table_row(row) for row in table.rows],
        ]

    def _visible_label_for_element(
        self, resolved: ResolvedElement, visible_labels: dict[str, str]
    ) -> str:
        return visible_labels[resolved.report_element.reference_token]

    def _render_table_row(self, cells: list[str]) -> str:
        return "| " + " | ".join(self._escape_table_cell(cell) for cell in cells) + " |"

    def _escape_table_cell(self, value: str) -> str:
        return value.replace("|", r"\|")
