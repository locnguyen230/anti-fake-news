"""Build a local, unpacked Chromium extension from versioned sources."""

import argparse
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "extension"
DEFAULT_OUTPUT = ROOT / "release" / "extension"
RUNTIME_CONFIG = Path("afn-runtime-config.json")
TOP_LEVEL = (
    "manifest.json",
    "popup.html",
    "popup.js",
    "styles/popup.css",
    "extract.js",
)
MODULES = (
    "api-client.js",
    "error-recovery.js",
    "image-selection.js",
    "request-lifecycle.js",
    "result-view.js",
)


def source_files():
    files = [Path(name) for name in TOP_LEVEL]
    files.extend(Path("modules") / name for name in MODULES)
    for relative in files:
        source = SOURCE / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Invalid extension source: {relative.as_posix()}")
    return files


def runtime_config(token, port=8000):
    if not token or not token.strip() or token != token.strip():
        raise ValueError("Set a valid AFN_DEMO_TOKEN in the environment or the repository .env")
    if not 1 <= port <= 65535:
        raise ValueError("AFN_PORT must be between 1 and 65535")

    return json.dumps({"endpoint": f"http://127.0.0.1:{port}", "demoToken": token}).encode("utf-8")


def config_from_environment():
    env_file = dotenv_values(ROOT / ".env", encoding="utf-8")
    token = os.environ.get("AFN_DEMO_TOKEN", env_file.get("AFN_DEMO_TOKEN"))
    try:
        port = int(os.environ.get("AFN_PORT", env_file.get("AFN_PORT", "8000")))
    except (TypeError, ValueError):
        raise ValueError("AFN_PORT must be between 1 and 65535") from None
    return runtime_config(token, port)


def up_to_date(output, files, config):
    if not output.is_dir() or output.is_symlink():
        return False
    contents = list(output.rglob("*"))
    if any(path.is_symlink() for path in contents):
        return False
    if {path.relative_to(output) for path in contents if not path.is_dir()} != {*files, RUNTIME_CONFIG}:
        return False
    return (output / RUNTIME_CONFIG).read_bytes() == config and all(
        (output / relative).read_bytes() == (SOURCE / relative).read_bytes()
        for relative in files
    )


def build_extension(output, config):
    if output.is_symlink():
        raise ValueError("Choose a package directory without a symlink")
    output = output.resolve()
    if output == SOURCE or SOURCE in output.parents:
        raise ValueError("Choose a destination outside the extension source folder")
    files = source_files()
    if output.exists():
        if up_to_date(output, files, config):
            return len(files) + 1
        raise FileExistsError("Choose a new output directory for the updated extension")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="afn-extension-", dir=output.parent) as temporary:
        staged = Path(temporary) / "unpacked"
        for relative in files:
            destination = staged / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relative, destination)
        (staged / RUNTIME_CONFIG).write_bytes(config)
        staged.rename(output)
    return len(files) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        count = build_extension(args.output, config_from_environment())
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Unpacked Chromium extension: {args.output.resolve()} ({count} files)")


if __name__ == "__main__":
    main()
