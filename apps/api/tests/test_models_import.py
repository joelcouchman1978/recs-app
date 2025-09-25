def test_models_import():
    # Importing models must not raise
    import apps.api.app.models as _  # noqa: F401
