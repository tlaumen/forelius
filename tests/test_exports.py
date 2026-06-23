def test_package_root_exports_implemented_public_api() -> None:
    import forelius

    assert forelius.initialize is not None
    assert forelius.ensure_initialized is not None
    assert forelius.ForeliusConfigurationError is not None
    assert forelius.InteractiveReportAborted is not None
    assert forelius.prompt_for_report is not None
    assert forelius.ReportConfig is not None
    assert forelius.ChapterSpec is not None
    assert forelius.Plot is not None
    assert forelius.Table is not None
    assert forelius.generate_plot_from_freeform is not None
