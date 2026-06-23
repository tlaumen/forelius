from __future__ import annotations

from pathlib import Path

from baml_client import types as baml_types
from pydantic import BaseModel

from forelius.elements import Plot
from forelius.initialization import ensure_initialized
from forelius.plotting.data import (
    DatasetMetadata,
    ExtractedColumn,
    ExtractedDataset,
    ValidatedDataset,
    build_dataset_metadata,
    number_input_lines,
    validate_extracted_dataset,
)
from forelius.plotting.render import render_xy_plot


class PlotGenerationSession(BaseModel):
    dataset: ValidatedDataset
    intent: baml_types.XYPlotIntent
    plot: Plot
    output_dir: Path

    def revise(self, feedback: str) -> "PlotGenerationSession":
        ensure_initialized()

        from baml_client.sync_client import b

        metadata = _internal_metadata_to_baml(build_dataset_metadata(self.dataset))
        revised_intent = b.ReviseXYPlotIntent(
            baml_types.ReviseXYPlotIntentInput(
                current_intent=self.intent,
                feedback=feedback,
                dataset=metadata,
            )
        )
        revised_plot = render_xy_plot(
            self.dataset,
            revised_intent,
            self.output_dir,
            filename_stem=self.plot.path.stem,
            overwrite=True,
        )
        return PlotGenerationSession(
            dataset=self.dataset,
            intent=revised_intent,
            plot=revised_plot,
            output_dir=self.output_dir,
        )


def generate_plot_session(
    request: str,
    output_dir: Path,
    filename_stem: str | None = None,
) -> PlotGenerationSession:
    ensure_initialized()

    from baml_client.sync_client import b

    extracted = b.ExtractDatasetFromFreeform(number_input_lines(request))
    dataset = validate_extracted_dataset(_baml_extracted_dataset_to_internal(extracted))
    metadata = _internal_metadata_to_baml(build_dataset_metadata(dataset))
    intent = b.CreateXYPlotIntent(
        baml_types.CreateXYPlotIntentInput(
            request=request,
            dataset=metadata,
        )
    )
    plot = render_xy_plot(dataset, intent, Path(output_dir), filename_stem)
    return PlotGenerationSession(
        dataset=dataset,
        intent=intent,
        plot=plot,
        output_dir=Path(output_dir),
    )


def generate_plot_from_freeform(
    request: str,
    output_dir: Path,
    filename_stem: str | None = None,
) -> Plot:
    return generate_plot_session(request, output_dir, filename_stem).plot


def _baml_extracted_dataset_to_internal(
    dataset: baml_types.ExtractedDataset,
) -> ExtractedDataset:
    return ExtractedDataset(
        data_start_line=dataset.data_start_line,
        data_end_line=dataset.data_end_line,
        confidence=_baml_enum_value_to_lower(dataset.confidence),
        assumptions=list(dataset.assumptions),
        columns=[
            ExtractedColumn(
                name=column.name,
                unit=column.unit,
                data_type=_baml_enum_value_to_lower(column.data_type),
                values=list(column.values),
            )
            for column in dataset.columns
        ],
    )


def _internal_metadata_to_baml(
    metadata: DatasetMetadata,
) -> baml_types.DatasetMetadata:
    return baml_types.DatasetMetadata(
        columns=[
            baml_types.DatasetColumnMetadata(
                name=column.name,
                unit=column.unit,
                data_type=_internal_data_type_to_baml(column.data_type),
            )
            for column in metadata.columns
        ],
        assumptions=list(metadata.assumptions),
    )


def _internal_data_type_to_baml(data_type: str) -> baml_types.ExtractedDataType:
    return baml_types.ExtractedDataType(data_type.upper())


def _baml_enum_value_to_lower(value) -> str:
    return value.value.lower()
