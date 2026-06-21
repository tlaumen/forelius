from enum import Enum
from pathlib import Path

from pydantic import BaseModel, field_validator, model_validator


class ElementKind(str, Enum):
    FIGURE = "figure"
    TABLE = "table"


class Plot(BaseModel):
    caption: str
    path: Path

    @field_validator("path")
    @classmethod
    def validate_path_exists(cls, path: Path) -> Path:
        if not path.exists():
            raise ValueError("Plot path must exist")
        return path


class Table(BaseModel):
    caption: str
    headers: list[str]
    rows: list[list[str]]

    @model_validator(mode="after")
    def validate_row_lengths(self) -> "Table":
        expected_length = len(self.headers)
        for row in self.rows:
            if len(row) != expected_length:
                raise ValueError("Every table row must have the same length as headers")
        return self


class ReportElement(BaseModel):
    element_id: str
    kind: ElementKind
    caption: str
    placement_token: str
    reference_token: str


class ResolvedElement(BaseModel):
    original: Plot | Table
    report_element: ReportElement


class ElementRegistry:
    def __init__(self) -> None:
        self._elements_by_object_id: dict[int, ResolvedElement] = {}
        self._figure_count = 0
        self._table_count = 0

    def register_all(self, items: list[Plot | Table]) -> None:
        for item in items:
            self._register(item)

    def resolve(self, items: list[Plot | Table]) -> list[ResolvedElement]:
        self.register_all(items)
        return [self._elements_by_object_id[id(item)] for item in items]

    def _register(self, item: Plot | Table) -> None:
        object_id = id(item)
        if object_id in self._elements_by_object_id:
            return

        if isinstance(item, Plot):
            report_element = self._build_figure_element(item)
        else:
            report_element = self._build_table_element(item)

        self._elements_by_object_id[object_id] = ResolvedElement(
            original=item,
            report_element=report_element,
        )

    def _build_figure_element(self, item: Plot) -> ReportElement:
        self._figure_count += 1
        element_id = f"fig_{self._figure_count:04d}"
        return ReportElement(
            element_id=element_id,
            kind=ElementKind.FIGURE,
            caption=item.caption,
            placement_token=f"<<FIG:{element_id}>>",
            reference_token=f"<<REF:{element_id}>>",
        )

    def _build_table_element(self, item: Table) -> ReportElement:
        self._table_count += 1
        element_id = f"tbl_{self._table_count:04d}"
        return ReportElement(
            element_id=element_id,
            kind=ElementKind.TABLE,
            caption=item.caption,
            placement_token=f"<<TBL:{element_id}>>",
            reference_token=f"<<REF:{element_id}>>",
        )
