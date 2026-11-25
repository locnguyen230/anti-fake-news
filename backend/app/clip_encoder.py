"""Frozen CLIP encoder shared by training and Backend inference."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from app.config import REPO_ROOT
from app.preprocessing import EMBEDDING_DTYPE_NAME, PREPROCESS_VERSION

DEFAULT_CLIP_REFERENCE = REPO_ROOT / "configs" / "clip-reference.json"


class ImageEncoder(Protocol):
    """Anything that maps RGB PIL images to raw (un-normalised) feature rows."""

    identity: dict[str, str]
    dim: int

    def encode(self, images: list[Any]) -> np.ndarray: ...


class ClipImageEncoder:
    """Pinned, frozen CLIP ViT-B/32 from configs/clip-reference.json (AFN-006)."""

    def __init__(self, reference: Path | str = DEFAULT_CLIP_REFERENCE, *,
                 cache_dir: Path | str | None = None, offline: bool = False) -> None:
        import torch
        from huggingface_hub import snapshot_download
        from transformers import CLIPImageProcessor, CLIPModel

        ref = json.loads(Path(reference).read_text(encoding="utf-8"))
        enc = ref["encoder"]
        runtime = ref["runtime"]
        if cache_dir is None:
            env = os.environ.get(runtime["cache_env"])
            cache_dir = Path(env) / "hub" if env else REPO_ROOT / runtime["default_cache_dir"] / "hub"
        local = snapshot_download(repo_id=enc["repo_id"], revision=enc["revision"],
                                  allow_patterns=enc["files"], cache_dir=str(cache_dir),
                                  local_files_only=offline)
        self._torch = torch
        self.model = CLIPModel.from_pretrained(
            local, dtype=torch.float32, local_files_only=offline
        ).eval()
        self.model.requires_grad_(False)
        self.processor = CLIPImageProcessor.from_pretrained(local, local_files_only=offline)
        self.dim = int(self.model.config.projection_dim)
        if self.dim != int(ref["embedding"]["dim"]):
            raise ValueError("CLIP projection_dim differs from clip-reference.json")
        processor_cfg = (Path(local) / "preprocessor_config.json").read_bytes()
        self.identity = {
            "repo_id": enc["repo_id"],
            "revision": enc["revision"],
            "processor_config_sha256": hashlib.sha256(processor_cfg).hexdigest(),
            "preprocess_version": PREPROCESS_VERSION,
            "dtype": EMBEDDING_DTYPE_NAME,
        }

    def encode(self, images: list[Any]) -> np.ndarray:
        inputs = self.processor(images=images, return_tensors="pt")
        with self._torch.inference_mode():
            out = self.model.get_image_features(pixel_values=inputs["pixel_values"])
        feats = out if isinstance(out, self._torch.Tensor) else out.pooler_output
        return feats.detach().cpu().numpy()
