import sys
from pathlib import Path

# Add project root to Python path so 'app' can be imported from tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
