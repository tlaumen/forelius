from __future__ import annotations

from enum import Enum
from typing import Any, Iterator

from forelius.chapter import ChapterRole, ChapterSpec
from forelius.config import ChapterRef, ReportConfig
from forelius.elements import ElementRegistry
from forelius.initialization import ensure_initialized
from forelius.section import Section, parse_section


class GenerationOrder(str, Enum):
    REPORT = "report"
    INTRODUCTION_LAST = "introduction_last"


class ChapterGenerator:
    def __init__(
        self,
        config: ReportConfig,
        chapter: ChapterRef,
        spec: ChapterSpec,
        registry: ElementRegistry,
    ) -> None:
        self.config = config
        self.chapter = chapter
        self.spec = spec
        self.registry = registry

    def generate(self) -> Section:
        resolved_elements = self.registry.resolve(self.spec.elements)
        chapter_input = {
            "config": self.config.model_dump(mode="json"),
            "chapter": self.chapter.model_dump(mode="json"),
            "pointers": list(self.spec.pointers),
            "elements": [
                resolved.report_element.model_dump(mode="json")
                for resolved in resolved_elements
            ],
        }
        text = self._dispatch(self.spec.role, chapter_input)
        return parse_section(self.chapter, text, resolved_elements)

    def draft(self) -> "ChapterDraft":
        return ChapterDraft(self)

    def _dispatch(self, role: ChapterRole, chapter_input: Any) -> str:
        ensure_initialized()

        from baml_client import types as baml_types
        from baml_client.sync_client import b

        baml_input = baml_types.ChapterInput(
            config=baml_types.ReportConfig(
                discipline=chapter_input["config"]["discipline"],
                subject=chapter_input["config"]["subject"],
                language=chapter_input["config"]["language"],
                figure_label=chapter_input["config"]["figure_label"],
                table_label=chapter_input["config"]["table_label"],
                outline=[
                    baml_types.ChapterRef(**chapter)
                    for chapter in chapter_input["config"]["outline"]
                ],
            ),
            chapter=baml_types.ChapterRef(**chapter_input["chapter"]),
            pointers=list(chapter_input["pointers"]),
            elements=[
                baml_types.ReportElement(**element)
                for element in chapter_input["elements"]
            ],
        )

        if role is ChapterRole.INTRODUCTION:
            return b.ReportIntroduction(baml_input)
        if role is ChapterRole.BODY:
            return b.ReportChapter(baml_input)
        if role is ChapterRole.CONCLUSION:
            return b.ReportConclusion(baml_input)

        raise ValueError(f"Unsupported chapter role: {role}")


class ChapterDraft:
    def __init__(self, generator: ChapterGenerator) -> None:
        self._generator = generator
        self._current = generator.generate()

    def current(self) -> Section:
        return self._current

    def pointers(self) -> list[str]:
        return list(self._generator.spec.pointers)

    def revise(self, pointers: list[str]) -> Section:
        revised_spec = self._generator.spec.with_additional_pointers(pointers)
        revised_generator = ChapterGenerator(
            config=self._generator.config,
            chapter=self._generator.chapter,
            spec=revised_spec,
            registry=self._generator.registry,
        )
        self._generator = revised_generator
        self._current = revised_generator.generate()
        return self._current

    def accept(self) -> Section:
        return self._current


def chapter_generators(
    config: ReportConfig,
    specs: list[ChapterSpec],
    generation_order: GenerationOrder = GenerationOrder.REPORT,
) -> Iterator[ChapterGenerator]:
    outline = [ChapterRef(number=index + 1, title=spec.title) for index, spec in enumerate(specs)]
    runtime_config = config.model_copy(update={"outline": outline})
    registry = ElementRegistry()
    generators = [
        ChapterGenerator(
            config=runtime_config,
            chapter=outline[index],
            spec=spec,
            registry=registry,
        )
        for index, spec in enumerate(specs)
    ]

    if generation_order is GenerationOrder.REPORT:
        yield from generators
        return

    if generation_order is GenerationOrder.INTRODUCTION_LAST:
        yield from [
            generator
            for generator in generators
            if generator.spec.role is not ChapterRole.INTRODUCTION
        ]
        yield from [
            generator
            for generator in generators
            if generator.spec.role is ChapterRole.INTRODUCTION
        ]
        return

    raise ValueError(f"Unsupported generation order: {generation_order}")


def order_sections(
    sections: list[Section],
    generation_order: GenerationOrder = GenerationOrder.REPORT,
) -> list[Section]:
    if generation_order is GenerationOrder.REPORT:
        return list(sections)

    if generation_order is GenerationOrder.INTRODUCTION_LAST:
        return sorted(sections, key=lambda section: section.chapter.number)

    raise ValueError(f"Unsupported generation order: {generation_order}")


def generate_report(
    config: ReportConfig,
    specs: list[ChapterSpec],
    generation_order: GenerationOrder = GenerationOrder.REPORT,
) -> list[Section]:
    sections = [
        generator.generate()
        for generator in chapter_generators(config, specs, generation_order)
    ]
    return order_sections(sections, generation_order)
