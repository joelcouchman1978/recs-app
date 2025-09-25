import importlib
import sys
import pathlib
root = pathlib.Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
modules = [
    "apps.api.app.routers.health",
    "apps.api.app.models",
    "apps.api.app.recs",
]
for m in modules:
    importlib.import_module(m)
