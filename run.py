"""
Startup launcher for Sustainable AI Crop Irrigation System.
Can be executed directly from the project root:
    python run.py
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app

if __name__ == "__main__":
    print("=" * 60)
    print("🌱 Sustainable AI Crop Irrigation System Server")
    print("   Web UI:  http://127.0.0.1:5000")
    print("   API Doc: http://127.0.0.1:5000/api/status")
    print("=" * 60)
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )
