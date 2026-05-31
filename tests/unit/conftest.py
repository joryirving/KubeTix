import sys
from pathlib import Path

# Ensure kubetix-api is on the path for test imports
# __file__ is in tests/unit/, so parent.parent.parent = repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kubetix-api"))
