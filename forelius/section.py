import re

from pydantic import BaseModel

from forelius.config import ChapterRef
from forelius.elements import ResolvedElement

PLACEMENT_TOKEN_PATTERN = re.compile(r"^<<(?:FIG|TBL):(?:fig|tbl)_\d{4}>>$")
PLACEMENT_TOKEN_SEARCH_PATTERN = re.compile(r"<<(?:FIG|TBL):(?:fig|tbl)_\d{4}>>")
REFERENCE_TOKEN_PATTERN = re.compile(r"<<REF:(?:fig|tbl)_\d{4}>>")


class SectionParseError(ValueError):
    pass


class Section(BaseModel):
    chapter: ChapterRef
    text: str
    line_element_map: dict[int, ResolvedElement]


def parse_section(
    chapter: ChapterRef,
    text: str,
    elements: list[ResolvedElement],
) -> Section:
    elements_by_placement_token = {
        element.report_element.placement_token: element for element in elements
    }
    expected_placement_tokens = set(elements_by_placement_token)
    seen_placement_tokens: set[str] = set()
    line_element_map: dict[int, ResolvedElement] = {}

    for line_number, line in enumerate(text.splitlines()):
        stripped_line = line.strip()
        if PLACEMENT_TOKEN_PATTERN.fullmatch(stripped_line):
            if stripped_line not in elements_by_placement_token:
                raise SectionParseError(f"Unknown placement token: {stripped_line}")
            if stripped_line in seen_placement_tokens:
                raise SectionParseError(f"Duplicate placement token: {stripped_line}")

            seen_placement_tokens.add(stripped_line)
            line_element_map[line_number] = elements_by_placement_token[stripped_line]
        elif PLACEMENT_TOKEN_SEARCH_PATTERN.search(line):
            raise SectionParseError("Placement tokens must appear on their own line")

        for reference_token in REFERENCE_TOKEN_PATTERN.findall(line):
            if reference_token not in {
                element.report_element.reference_token for element in elements
            }:
                raise SectionParseError(f"Unknown reference token: {reference_token}")

    missing_placement_tokens = expected_placement_tokens - seen_placement_tokens
    if missing_placement_tokens:
        formatted_missing = ", ".join(sorted(missing_placement_tokens))
        raise SectionParseError(f"Missing placement token(s): {formatted_missing}")

    return Section(chapter=chapter, text=text, line_element_map=line_element_map)
