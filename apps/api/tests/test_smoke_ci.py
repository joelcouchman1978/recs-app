import importlib
import sys
import pathlib
root = pathlib.Path(__file__).resolve().parents[2]
api_dir = root / "apps" / "api"
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))
for mod in [
    "app.recs",
    "app.models",
    "app.routers.health",
]:
    importlib.import_module(mod)
