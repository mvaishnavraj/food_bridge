"""
FoodBridge - One-Click Launcher
Starts the Flask backend server and launches the frontend web application.
"""

import os
import sys
import webbrowser
from threading import Timer

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    print("================================================================")
    print(" [FoodBridge] AI-Assisted Surplus Food Redistribution System")
    print("================================================================")
    print(" [*] Initializing SQLite database and seeding demo records...")
    print(" [*] Starting Flask REST Server on http://127.0.0.1:5000 ...")
    print(" [*] VLM Vision Model (Ollama/LLaVA + Fallback) Ready")
    print(" [*] Open-Meteo Weather Urgency Engine Active")
    print("================================================================")
    print(" Press CTRL+C to terminate the server.\n")

    Timer(1.5, open_browser).start()

    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    sys.path.insert(0, backend_dir)

    from app import app
    app.run(host="0.0.0.0", port=5000, debug=False)

