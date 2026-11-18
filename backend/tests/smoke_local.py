"""Optional real-socket smoke: run from backend with `python tests/smoke_local.py`.

Uses the documented Uvicorn command and always stops the child it starts.
No model, credentials or uploaded article/image is needed.
"""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def main() -> None:
    # Refuse to test against or stop an unrelated server already using this port.
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 8000))

    command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host",
               "127.0.0.1", "--port", "8000", "--no-access-log"]
    process = subprocess.Popen(
        command, cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    opener = build_opener(ProxyHandler({}))
    try:
        deadline = time.monotonic() + 15
        while True:
            if process.poll() is not None:
                raise RuntimeError("Uvicorn exited before startup")
            try:
                with opener.open("http://127.0.0.1:8000/health", timeout=1) as response:
                    assert response.status == 200
                    assert json.load(response) == {
                        "service_status": "ok", "model_ready": False,
                        "contract_version": "0.1.0",
                    }
                break
            except (URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Uvicorn startup timed out") from None
                time.sleep(0.1)
        print("GET /health: 200; model_ready=false")
        try:
            opener.open(Request("http://127.0.0.1:8000/predict", method="POST"), timeout=2)
        except HTTPError as response:
            with response:
                assert response.code == 503
                assert json.load(response) == {
                    "detail": "Model is not ready", "error_code": "model_not_ready",
                    "request_id": None,
                }
        else:
            raise AssertionError("Prediction must not succeed")
        print("POST /predict: 503; model_not_ready; request_id=null")
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)
        # Startup logs only; no request bodies or credentials are sent by this test.
        print(output.strip())
        print("Stopped smoke server process:", process.poll() is not None)


if __name__ == "__main__":
    main()
