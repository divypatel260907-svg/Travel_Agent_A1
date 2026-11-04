import sys
from pathlib import Path

# Add project root and travel_planner directory to sys.path
_HERE = Path(__file__).resolve().parent          # api/
_ROOT = _HERE.parent                             # project root (ibm-bob/)
_PKG = _ROOT / "travel_planner"                  # travel_planner/

for p in (_ROOT, _PKG):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app import create_app

app = create_app("production")

