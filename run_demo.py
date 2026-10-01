"""
Filestavk Demo Runner.
Launches Filestavk in 100% Anonymized Demo Mode:
- Connects to backend/data/filestavk_demo.db (isolated test database)
- Seeds realistic mock clients, cause numbers, and vouchers if not present
- Applies clean commercial practice branding ("Coastal Operations & Practice" / "Kimbel B.")
- Starts both FastAPI backend (port 8000) and Vite frontend (port 5173)
- Shuts down cleanly on Ctrl+C without touching the production database (filestavk.db)
"""

import os
import sys
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
DEMO_DB = BACKEND_DIR / "data" / "filestavk_demo.db"

# Find python in virtual environment
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

def main():
    print("=" * 64)
    print("      FILESTAVK - ANONYMIZED DEMO & MARKETING ENVIRONMENT")
    print("=" * 64)
    print(f"[*] Demo Database: {DEMO_DB.relative_to(ROOT_DIR)}")
    print("[*] Active Persona: Kimbel B. | Coastal Operations & Practice")
    print("[*] Status: 100% Anonymized / Safe for Public Demos & Nextdoor")
    print("=" * 64)

    # 1. Seed demo database if missing or if --reset passed
    if not DEMO_DB.exists() or "--reset" in sys.argv:
        print("\n[+] Seeding demo database with clean mock data...")
        env_seed = os.environ.copy()
        env_seed["FILESTAVK_DEMO"] = "true"
        env_seed["PYTHONPATH"] = str(BACKEND_DIR)
        res = subprocess.run(
            [str(VENV_PYTHON), str(BACKEND_DIR / "scripts" / "seed_demo_data.py")],
            cwd=str(BACKEND_DIR),
            env=env_seed,
        )
        if res.returncode != 0:
            print("[-] Failed to seed demo database.")
            return

    # 2. Prepare environment for backend
    backend_env = os.environ.copy()
    backend_env["FILESTAVK_DEMO"] = "true"
    backend_env["PYTHONPATH"] = str(BACKEND_DIR)

    print("\n[+] Starting FastAPI backend on http://127.0.0.1:8000 (DEMO MODE)...")
    backend_proc = subprocess.Popen(
        [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=str(BACKEND_DIR),
        env=backend_env,
    )

    time.sleep(1.5)

    print("[+] Starting Vite frontend on http://localhost:5173...")
    # Use npm or npx
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    print("\n" + "*" * 64)
    print("  Filestavk Demo is LIVE!")
    print("  -> Open your browser to: http://localhost:5173")
    print("  -> Press Ctrl+C in this window at any time to stop.")
    print("*" * 64 + "\n")

    try:
        while True:
            time.sleep(0.5)
            if backend_proc.poll() is not None or frontend_proc.poll() is not None:
                break
    except KeyboardInterrupt:
        print("\n[*] Stopping demo servers gracefully...")
    finally:
        if backend_proc.poll() is None:
            backend_proc.terminate()
        if frontend_proc.poll() is None:
            frontend_proc.terminate()
        print("[✓] Demo environment stopped. Production database remains untouched.")

if __name__ == "__main__":
    main()
