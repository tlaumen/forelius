def test_package_imports_without_initialization() -> None:
    import forelius

    assert forelius is not None
