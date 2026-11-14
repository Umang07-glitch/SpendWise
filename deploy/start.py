"""Run both servers as one service; fail the container if either server exits."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import urlopen


def stop(processes):
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def wait_for_backend(process, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Backend exited during startup")
        try:
            with urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Backend did not become healthy within startup timeout")


def main():
    root = Path(__file__).resolve().parents[1]
    port = int(os.environ.get("PORT", "10000"))
    if port == 8000 or not 1 <= port <= 65535:
        raise ValueError("PORT must be a valid port other than the internal API port 8000")
    # Never seed production automatically. Every registration starts empty.
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root / "backend", check=True)
    processes = []

    def shutdown(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        processes.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=root / "backend"))
        wait_for_backend(processes[0])
        processes.append(subprocess.Popen(
            [os.environ.get("NODE_BINARY", "node"), "server.js"], cwd=root / "frontend",
            env={**os.environ, "HOSTNAME": "0.0.0.0", "PORT": str(port)}))
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        return 1
    finally:
        stop(processes)


if __name__ == "__main__":
    sys.exit(main())
