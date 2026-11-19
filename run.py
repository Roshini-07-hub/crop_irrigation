"""
Startup launcher for Sustainable AI Crop Irrigation System.
Can be executed directly from the project root:
    python run.py
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🌱 Sustainable AI Crop Irrigation System Server")
    print(f"   Port:    {port}")
    print(f"   API Doc: http://0.0.0.0:{port}/api/status")
    print("=" * 60)
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
