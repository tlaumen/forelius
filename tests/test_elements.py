from forelius.elements import ElementKind, ElementRegistry, Plot, Table


def make_plot(tmp_path, name="plot.png") -> Plot:
    image_path = tmp_path / name
    image_path.write_bytes(b"plot")
    return Plot(caption="Settlement profile", path=image_path)


def test_registry_resolves_figure_tokens(tmp_path) -> None:
    plot = make_plot(tmp_path)
    registry = ElementRegistry()

    resolved = registry.resolve([plot])[0]

    assert resolved.original is plot
    assert resolved.report_element.element_id == "fig_0001"
    assert resolved.report_element.kind is ElementKind.FIGURE
    assert resolved.report_element.caption == "Settlement profile"
    assert resolved.report_element.placement_token == "<<FIG:fig_0001>>"
    assert resolved.report_element.reference_token == "<<REF:fig_0001>>"


def test_registry_resolves_table_tokens() -> None:
    table = Table(caption="Loads", headers=["Case", "Load"], rows=[["A", "10 kN"]])
    registry = ElementRegistry()

    resolved = registry.resolve([table])[0]

    assert resolved.original is table
    assert resolved.report_element.element_id == "tbl_0001"
    assert resolved.report_element.kind is ElementKind.TABLE
    assert resolved.report_element.placement_token == "<<TBL:tbl_0001>>"
    assert resolved.report_element.reference_token == "<<REF:tbl_0001>>"


def test_registry_uses_independent_figure_and_table_counters(tmp_path) -> None:
    plot = make_plot(tmp_path)
    table = Table(caption="Loads", headers=["Case", "Load"], rows=[["A", "10 kN"]])
    registry = ElementRegistry()

    resolved = registry.resolve([plot, table])

    assert resolved[0].report_element.element_id == "fig_0001"
    assert resolved[1].report_element.element_id == "tbl_0001"


def test_registry_registration_is_incremental(tmp_path) -> None:
    first = make_plot(tmp_path, "first.png")
    second = make_plot(tmp_path, "second.png")
    registry = ElementRegistry()

    first_resolved = registry.resolve([first])[0]
    second_resolved = registry.resolve([second])[0]

    assert first_resolved.report_element.element_id == "fig_0001"
    assert second_resolved.report_element.element_id == "fig_0002"


def test_registry_registration_is_idempotent_for_same_object(tmp_path) -> None:
    plot = make_plot(tmp_path)
    registry = ElementRegistry()

    first = registry.resolve([plot])[0]
    second = registry.resolve([plot])[0]

    assert first is second
    assert second.report_element.element_id == "fig_0001"


def test_registry_assigns_distinct_ids_to_equivalent_copied_objects(tmp_path) -> None:
    plot = make_plot(tmp_path)
    copied_plot = plot.model_copy()
    registry = ElementRegistry()

    resolved = registry.resolve([plot, copied_plot])

    assert resolved[0].report_element.element_id == "fig_0001"
    assert resolved[1].report_element.element_id == "fig_0002"
