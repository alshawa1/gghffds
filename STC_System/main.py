"""
Maharah Operations Automation System
STC Operations

Entry point — run this file to start the application:
    python main.py
"""
import sys
import os

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gui.app import Application


def main():
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
