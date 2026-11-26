"""Package the portable production Backend as a ZIP."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    ".env.example",
    "backend/app/__init__.py",
    "backend/app/__main__.py",
    "backend/app/clip_encoder.py",
    "backend/app/config.py",
    "backend/app/cors.py",
    "backend/app/errors.py",
    "backend/app/image_validation.py",
    "backend/app/inference_adapter.py",
    "backend/app/lifespan.py",
    "backend/app/main.py",
    "backend/app/model_bundle.py",
    "backend/app/model_loader.py",
    "backend/app/predictor.py",
    "backend/app/preprocessing.py",
    "backend/app/schemas.py",
    "backend/app/validation.py",
    "backend/artifacts/metadata.schema.json",
    "backend/requirements.txt",
    "configs/clip-reference.json",
    "docs/backend-setup.md",
    "ml/requirements.txt",
    "release/backend-checklist.md",
)


def build_backend(output: Path) -> None:
    for name in RUNTIME_FILES:
        source = ROOT / name
        if not source.is_file() or source.resolve() != source:
            raise ValueError(f"Invalid package source: {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for name in RUNTIME_FILES:
            archive.write(ROOT / name, name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "release" / "backend.zip")
    args = parser.parse_args()
    try:
        build_backend(args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Backend package: {args.output} ({len(RUNTIME_FILES)} files)")


if __name__ == "__main__":
    main()
