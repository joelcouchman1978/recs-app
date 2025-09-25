import importlib

def test_api_imports_lightweight():
    for mod in [
        "apps.api.app.recs",
        "apps.api.app.models",
        "apps.api.app.routers.health",
    ]:
        importlib.import_module(mod)
