from pydantic import BaseModel, Field


class ChapterRef(BaseModel):
    number: int
    title: str


class ReportConfig(BaseModel):
    discipline: str
    subject: str
    language: str
    figure_label: str
    table_label: str
    outline: list[ChapterRef] = Field(default_factory=list)
