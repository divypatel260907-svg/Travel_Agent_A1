"""Vercel / Root entrypoint for Flask app."""
import sys
from pathlib import Path

# Add project root and travel_planner directory to sys.path
_ROOT = Path(__file__).resolve().parent
_PKG = _ROOT / "travel_planner"

for p in (_ROOT, _PKG):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app import create_app

app = create_app("production")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
