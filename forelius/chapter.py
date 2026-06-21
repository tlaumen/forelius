from enum import Enum

from pydantic import BaseModel, Field

from forelius.elements import Plot, Table


class ChapterRole(str, Enum):
    INTRODUCTION = "introduction"
    BODY = "body"
    CONCLUSION = "conclusion"


class ChapterSpec(BaseModel):
    role: ChapterRole
    title: str
    pointers: list[str] = Field(default_factory=list)
    elements: list[Plot | Table] = Field(default_factory=list)

    def with_feedback(self, feedback: str) -> "ChapterSpec":
        return self.model_copy(update={"pointers": [*self.pointers, feedback]})
