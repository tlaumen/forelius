from typing import Protocol

from forelius.config import ReportConfig
from forelius.section import Section


class ReportRenderer(Protocol):
    def render(self, config: ReportConfig, sections: list[Section]) -> str: ...
