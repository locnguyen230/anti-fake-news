"""AFN-052: real offline Backend benchmark on synthetic, non-Test inputs.

Supervisor starts its own loopback server, measures actual HTTP requests, and
stops it gracefully. Candidate evidence is explicitly provisional. No training,
model edits, raw articles, credentials or absolute paths enter the JSON report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import secrets
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def statistics_ms(values: list[float]) -> dict:
    if not values or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError("Expected nonnegative finite timings")
    ordered = sorted(values)
    return {"n": len(values), "min": min(values), "median": statistics.median(values),
            "p95_nearest_rank": ordered[math.ceil(.95 * len(values)) - 1], "max": max(values)}


def preflight(bundle: Path, candidate: bool, freeze: Path) -> dict:
    metadata_bytes = (bundle / "metadata.json").read_bytes()
    meta = json.loads(metadata_bytes)
    expected = "candidate" if candidate else "frozen"
    if (meta.get("is_fixture") is not False or meta.get("configuration") != "multimodal"
            or meta.get("status") != expected):
        raise ValueError("Expected a real multimodal bundle with the selected status")
    if not candidate:
        # Signed freeze verification reads Train/Validation and bundle hashes only.
        import ml
        from ml.freeze import read_record, verify
        verify(read_record(freeze), bundle_root=bundle.parent)
    return {"model_id": meta["model_id"], "model_version": meta["model_version"],
            "status": meta["status"], "is_fixture": False,
            "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
            "freeze_verified": not candidate}


def rss_reader():
    """Current process RSS/working set. No extra dependency or child-process RSS."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage")]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

        def read():
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                raise OSError("Cannot measure Backend working set")
            return counters.WorkingSetSize
        return read
    if sys.platform.startswith("linux"):
        def read():
            return int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        return read
    raise RuntimeError("RSS measurement currently supports Windows and Linux")


def installed_memory_mib():
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        memory = ctypes.c_ulonglong()
        kernel.GetPhysicallyInstalledSystemMemory.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)]
        if not kernel.GetPhysicallyInstalledSystemMemory(ctypes.byref(memory)):
            raise OSError("Cannot measure installed memory")
        return memory.value / 1024
    if sys.platform.startswith("linux"):
        line = next(line for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal:"))
        return int(line.split()[1]) / 1024
    raise RuntimeError("Machine inventory currently supports Windows and Linux")


class Resources:
    def __init__(self):
        self.read = rss_reader()
        self.start = time.perf_counter()
        self.cpu_start = time.process_time()
        self.baseline = self.read()
        self.peak = self.baseline
        self.samples = 0
        self.error = False
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self):
        while not self.stop.is_set():
            try:
                self.peak = max(self.peak, self.read())
                self.samples += 1
            except OSError:
                self.error = True
                return
            self.stop.wait(.05)

    def finish(self):
        self.stop.set()
        self.thread.join()
        if self.error:
            raise RuntimeError("Resource sampling failed")
        elapsed = time.perf_counter() - self.start
        cpu = time.process_time() - self.cpu_start
        return {"sampling_interval_ms": 50, "samples": self.samples,
                "rss_baseline_mib": self.baseline / 1024**2, "rss_peak_sampled_mib": self.peak / 1024**2,
                "cpu_seconds": cpu, "observed_wall_seconds": elapsed,
                "cpu_mean_percent_one_core": 100 * cpu / elapsed,
                "scope": "Backend worker only; imports, startup, requests, idle gaps and shutdown; CPU may exceed 100%"}


def write_json(path: Path, value: dict):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def worker(args):
    """Private benchmark process; instrumentation delegates to unchanged serving code."""
    import asyncio
    from contextlib import asynccontextmanager
    from importlib.metadata import version
    import socket

    resources = Resources()
    resources.thread.start()
    stages = {}
    start = time.perf_counter()
    import torch
    torch.set_num_threads(args.threads)
    import ml
    import uvicorn
    from app import model_loader
    from app.config import Settings
    from app.main import create_app
    from app.predictor import BundlePredictor
    stages["runtime_import_ms"] = (time.perf_counter() - start) * 1000

    def timed(name, function):
        def call(*pos, **kw):
            before = time.perf_counter()
            try:
                return function(*pos, **kw)
            finally:
                stages[name] = (time.perf_counter() - before) * 1000
        return call

    model_loader.load_bundle = timed("bundle_load_ms", model_loader.load_bundle)
    model_loader.ClipImageEncoder = timed("clip_load_ms", model_loader.ClipImageEncoder)
    model_loader.load_predictor = timed("loader_total_including_warmup_ms", model_loader.load_predictor)
    original_predict = BundlePredictor.predict

    def warmup(self, inputs):
        try:
            return timed("warmup_ms", original_predict)(self, inputs)
        finally:
            BundlePredictor.predict = original_predict
    BundlePredictor.predict = warmup
    settings = Settings(_env_file=None, environment="production", predictor_mode="real",
                        demo_token=os.environ["AFN_BENCH_TOKEN"], extension_origin=None,
                        model_artifact_path=args.bundle, model_metadata_sha256=args.metadata_sha256,
                        allow_candidate_model=args.candidate)
    app = create_app(settings)
    original_lifespan = app.router.lifespan_context
    ready_file = args.work / "ready.json"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

        @asynccontextmanager
        async def lifespan(app):
            before = time.perf_counter()
            async with original_lifespan(app):
                stages["lifespan_startup_ms"] = (time.perf_counter() - before) * 1000
                stages["loader_excluding_warmup_ms"] = stages["loader_total_including_warmup_ms"] - stages["warmup_ms"]
                write_json(ready_file, {"port": port, "stages": stages,
                    "versions": {name: version(name) for name in
                                 ("fastapi", "uvicorn", "torch", "transformers", "scikit-learn", "numpy", "scipy", "pillow")}})
                yield
            write_json(args.work / "cleanup.json", {"predictor_released": app.state.predictor is None,
                                                       "not_ready": not app.state.inference_adapter.ready})

        app.router.lifespan_context = lifespan
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, access_log=False))

        async def serve():
            async def stop_when_requested():
                while not (args.work / "stop").exists():
                    await asyncio.sleep(.05)
                server.should_exit = True
            watcher = asyncio.create_task(stop_when_requested())
            try:
                await server.serve(sockets=[sock])
            finally:
                watcher.cancel()
                await asyncio.gather(watcher, return_exceptions=True)
        try:
            asyncio.run(serve())
        finally:
            write_json(args.work / "resources.json", resources.finish())
    if not server.started:
        raise RuntimeError("Benchmark Backend did not start")


def synthetic_request():
    from io import BytesIO
    from PIL import Image
    with Image.new("RGB", (160, 120), (40, 120, 200)) as image, BytesIO() as buffer:
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
    request_id = str(uuid4())
    boundary = "afn-" + uuid4().hex
    parts = []
    for name, value in (("request_id", request_id), ("title", "Synthetic local benchmark"),
                        ("text", "The city council published the annual public transit maintenance report.")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="synthetic.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + image_bytes + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return request_id, b"".join(parts), "multipart/form-data; boundary=" + boundary


def benchmark(args) -> dict:
    identity = preflight(args.bundle, args.candidate, args.freeze)
    import ml
    from app.schemas import PredictResponse
    opener = build_opener(ProxyHandler({}))
    token = secrets.token_urlsafe(32)
    environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("AFN_")}
    environment.update(AFN_BENCH_TOKEN=token, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    with tempfile.TemporaryDirectory(prefix="afn-benchmark-") as directory:
        work = Path(directory)
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--work", str(work),
                   "--bundle", str(args.bundle.resolve()), "--metadata-sha256", identity["metadata_sha256"],
                   "--threads", str(args.threads)]
        if args.candidate:
            command.append("--candidate")
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        with (work / "server.log").open("w+", encoding="utf-8") as log:
            before = time.perf_counter()
            process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log, stderr=log, **options)
            forced = False
            try:
                deadline = before + args.timeout
                ready = None
                while time.perf_counter() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError("Backend exited during benchmark startup")
                    if (work / "ready.json").exists():
                        ready = json.loads((work / "ready.json").read_text())
                        url = f'http://127.0.0.1:{ready["port"]}'
                        try:
                            with opener.open(url + "/health", timeout=1) as response:
                                if json.load(response)["model_ready"]:
                                    break
                        except (URLError, TimeoutError):
                            pass
                    time.sleep(.05)
                else:
                    raise RuntimeError("Benchmark startup timeout")
                startup_ms = (time.perf_counter() - before) * 1000
                measurements = []
                scores = []
                for _ in range(args.repeat + 1):
                    request_id, body, content_type = synthetic_request()
                    request = Request(url + "/predict", body,
                                      {"X-Demo-Token": token, "Content-Type": content_type})
                    start = time.perf_counter()
                    with opener.open(request, timeout=args.timeout) as response:
                        payload = json.load(response)
                        elapsed = (time.perf_counter() - start) * 1000
                        if response.status != 200 or response.headers["X-AFN-Inference-Mode"] != "real":
                            raise RuntimeError("Benchmark requires successful real inference")
                    result = PredictResponse.model_validate(payload)
                    if (str(result.request_id) != request_id or result.model_id != identity["model_id"]
                            or result.model_version != identity["model_version"]):
                        raise RuntimeError("Benchmark response identity mismatch")
                    scores.append((result.label, result.fake_score, result.text_truncated))
                    measurements.append({"server_ms": result.processing_time_ms, "http_ms": elapsed})
                if any(item != scores[0] for item in scores):
                    raise RuntimeError("Repeated prediction changed")
                with opener.open(url + "/health", timeout=2) as response:
                    if not json.load(response)["model_ready"]:
                        raise RuntimeError("Backend lost readiness")
            finally:
                (work / "stop").touch()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    forced = True
                    process.kill()
                    process.wait(timeout=5)
            log.seek(0)
            logged = log.read()
        if forced or process.returncode != 0 or not (work / "cleanup.json").exists():
            raise RuntimeError("Backend did not shut down gracefully")
        cleanup = json.loads((work / "cleanup.json").read_text())
        if not all(cleanup.values()):
            raise RuntimeError("Backend retained its provider after shutdown")
        if any(secret in logged for secret in (token, str(ROOT), str(args.bundle.resolve()), "Traceback (most recent call last)")):
            raise RuntimeError("Backend log hygiene check failed")
        resources = json.loads((work / "resources.json").read_text())
    server_stats = statistics_ms([m["server_ms"] for m in measurements[1:]])
    source_files = ["scripts/benchmark_local.py", "backend/requirements.txt", "ml/requirements.txt",
                    "configs/clip-reference.json", *[p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "backend/app").glob("*.py"))]]
    return {"schema": "afn-benchmark-v1", "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evidence": "CANDIDATE_SYNTHETIC_NOT_FINAL" if args.candidate else "FROZEN_SYNTHETIC",
            "bundle": identity, "machine": {"os": platform.platform(), "cpu": platform.processor(),
                "logical_cpus": os.cpu_count(), "installed_memory_mib": installed_memory_mib(),
                "python": platform.python_version(), "torch_threads": args.threads},
            "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files},
            "versions": ready["versions"], "startup_to_health_ms": startup_ms, "stages_ms": ready["stages"],
            "first_request": measurements[0], "subsequent_server_ms": server_stats,
            "subsequent_http_ms": statistics_ms([m["http_ms"] for m in measurements[1:]]),
            "requests": measurements, "resources": resources, "cleanup": cleanup,
            "log_hygiene_passed": True, "median_under_10s": server_stats["median"] < 10000,
            "scope": "Synthetic RGB PNG 160x120 and fixed English text; first HTTP request is AFTER startup warm-up. Server processing_time_ms excludes load/transport validation; HTTP includes transport validation and response transfer. Startup includes imports/load/warm-up and health polling. Timings overlap: loader total includes warm-up; not additive. RSS is sampled working set, not a leak proof."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--candidate", action="store_true", help="Explicit provisional candidate measurement")
    parser.add_argument("--freeze", type=Path, default=ROOT / "release/model-freeze.json")
    parser.add_argument("--repeat", type=int, default=20, help="Requests after the separately measured first request; >=20")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--work", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--metadata-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.repeat < 20 or args.threads < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("repeat must be >=20, threads >=1, timeout finite and positive")
    try:
        if args.worker:
            worker(args)
        else:
            report = benchmark(args)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                write_json(args.out, report)
            print(json.dumps(report, indent=2))
        return 0
    except Exception as error:
        # No private paths, credentials, model exception text or traceback.
        print(f"Benchmark failed ({type(error).__name__}); check bundle, offline cache and configuration.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
