"""
RAGeval Inference Adapter
==========================
Unified adapter for embedding inference that can't run on the 512MB Render free tier.
Mirrors the IntelAI inference_adapter.py pattern with dynamic dialect routing.

Env vars:
  RAGEVAL_INFERENCE_MODE=local|remote   (default: remote if RAGEVAL_REMOTE_ENDPOINT set)
  RAGEVAL_REMOTE_ENDPOINT=              (Target URL for remote embedding API)
  RAGEVAL_REMOTE_TOKEN=                 (bearer token — falls back to provider-specific keys)
  EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
  COHERE_API_KEY=
  HF_TOKEN= / HF_READ_TOKEN=
  HOSTED_EMBEDDING_MODEL=               (Explicit override for Cohere/HF remote models)
  RAGEVAL_EMBED_TIMEOUT=30
"""
from __future__ import annotations

import json as _json
import logging
import os
import threading
import time
import urllib.request
from typing import List, Optional

log = logging.getLogger(__name__)

_LAST_WAKE = 0.0

# Maps local embedding models to their closest Cohere equivalents
_COHERE_MODEL_MAP = {
    "baai/bge-large-en-v1.5": "embed-english-v3.0",
    "all-minilm-l6-v2": "embed-english-light-v3.0",
    "bge-m3": "embed-multilingual-v3.0",
    "baai/bge-m3": "embed-multilingual-v3.0",
    "default": "embed-english-v3.0",
}


def _remote_endpoint() -> str:
    return (os.getenv("RAGEVAL_REMOTE_ENDPOINT", "")
            or os.getenv("LIGHTNING_EMBED_URL", "")    # legacy
            or os.getenv("ORCHESTRATOR_URL", "")        # legacy
            or "").strip().rstrip("/")


def _remote_token() -> str:
    return (os.getenv("RAGEVAL_REMOTE_TOKEN", "")
            or os.getenv("INFERENCE_TOKEN", "")).strip()


def _use_local() -> bool:
    mode = os.getenv("RAGEVAL_INFERENCE_MODE", "").strip().lower()
    if mode == "local":
        return True
    if mode == "remote":
        return False
    # Default to remote if remote endpoint is set, otherwise local
    return not _remote_endpoint()


def _detect_dialect(url: str) -> str:
    url_lower = url.lower()
    if "cohere.com" in url_lower:
        return "cohere"
    if "huggingface" in url_lower:
        return "hf"
    if "orchestrator" in url_lower or "lightning" in url_lower:
        return "orchestrator"
    return "openai"


def _fire_wake():
    global _LAST_WAKE
    url = _remote_endpoint()
    if not url or (time.time() - _LAST_WAKE) < 60:
        return
    _LAST_WAKE = time.time()

    def _go():
        try:
            h = {"Content-Type": "application/json"}
            tk = _remote_token() or os.getenv("ORCH_TOKEN", "").strip()
            if tk:
                h["Authorization"] = f"Bearer {tk}"
            body = _json.dumps({"gpu": False, "service": "rageval"}).encode()
            req = urllib.request.Request(url + "/wake", data=body, headers=h)
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            log.debug("wake signal failed: %s", e)

    threading.Thread(target=_go, daemon=True).start()


def _call_remote_embed(
    url: str,
    token: str,
    texts: List[str],
    model: Optional[str] = None
) -> Optional[List[List[float]]]:
    dialect = _detect_dialect(url)
    timeout = int(os.getenv("RAGEVAL_EMBED_TIMEOUT", "30"))
    h = {"Content-Type": "application/json"}

    # Resolve token by dialect if default token not set
    if not token:
        if dialect == "cohere":
            token = os.getenv("COHERE_API_KEY", "").strip()
        elif dialect == "hf":
            token = (os.getenv("HF_TOKEN", "") or os.getenv("HF_READ_TOKEN", "")).strip()
        elif dialect == "orchestrator":
            token = os.getenv("ORCH_TOKEN", "").strip()

    if token:
        h["Authorization"] = f"Bearer {token}"

    try:
        if dialect == "cohere":
            if not url.endswith("/v2/embed"):
                url = url.rstrip("/") + "/v2/embed"
            
            # Map the local model name to Cohere's equivalent model
            resolved_model = os.getenv("HOSTED_EMBEDDING_MODEL", "").strip()
            if not resolved_model:
                model_key = (model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")).strip().lower()
                resolved_model = _COHERE_MODEL_MAP.get(model_key, _COHERE_MODEL_MAP["default"])

            payload = {
                "model": resolved_model,
                "texts": list(texts),
                "input_type": os.getenv("HOSTED_EMBED_INPUT_TYPE", "search_document"),
                "embedding_types": ["float"],
            }
            req = urllib.request.Request(url, data=_json.dumps(payload).encode(), headers=h)
            data = _json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            return data["embeddings"]["float"]

        elif dialect == "hf":
            m = model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
            
            # Map standard model names to full HF model IDs
            hf_model_id = m
            if m.lower() == "all-minilm-l6-v2":
                hf_model_id = "sentence-transformers/all-MiniLM-L6-v2"
            elif m.lower() == "bge-m3":
                hf_model_id = "BAAI/bge-m3"

            # HuggingFace hosted model override if provided
            override_model = os.getenv("HOSTED_EMBEDDING_MODEL", "").strip()
            if override_model:
                hf_model_id = override_model

            if not ("/models/" in url or "/pipeline/feature-extraction/" in url):
                url = url.rstrip("/") + f"/pipeline/feature-extraction/{hf_model_id}"
            payload = {"inputs": texts, "options": {"wait_for_model": True}}
            req = urllib.request.Request(url, data=_json.dumps(payload).encode(), headers=h)
            data = _json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            return data

        elif dialect == "orchestrator":
            if not url.endswith("/embed"):
                url = url.rstrip("/") + "/embed"
            payload: dict = {"texts": texts}
            if model:
                payload["model"] = model
            req = urllib.request.Request(url, data=_json.dumps(payload).encode(), headers=h)
            resp = _json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            return resp.get("embeddings")

        else:  # openai
            if not (url.endswith("/v1/embeddings") or url.endswith("/embeddings")):
                url = url.rstrip("/") + "/v1/embeddings"
            payload = {
                "input": texts,
                "model": model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
            }
            req = urllib.request.Request(url, data=_json.dumps(payload).encode(), headers=h)
            resp = _json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            return [item["embedding"] for item in resp["data"]]

    except Exception as e:
        log.warning("remote embed failed for dialect %s (%s)", dialect, e)
        if dialect == "orchestrator":
            _fire_wake()
        return None


_local_embedder = None


def _local_embed(texts: List[str], model: Optional[str] = None) -> Optional[List[List[float]]]:
    global _local_embedder
    m = model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
    try:
        from sentence_transformers import SentenceTransformer
        if _local_embedder is None or getattr(_local_embedder, "_name", "") != m:
            _local_embedder = SentenceTransformer(m)
            _local_embedder._name = m
        return _local_embedder.encode(texts, normalize_embeddings=True).tolist()
    except Exception as e:
        log.warning("local embed failed for model %s: %s", m, e)
        
        # Fallback to local lightweight option if BAAI/bge-large-en-v1.5 fails
        fallback = "all-MiniLM-L6-v2"
        if m != fallback:
            try:
                log.info("Attempting local fallback to lightweight model: %s", fallback)
                from sentence_transformers import SentenceTransformer
                if _local_embedder is None or getattr(_local_embedder, "_name", "") != fallback:
                    _local_embedder = SentenceTransformer(fallback)
                    _local_embedder._name = fallback
                return _local_embedder.encode(texts, normalize_embeddings=True).tolist()
            except Exception as fe:
                log.warning("local fallback embed failed: %s", fe)
        return None


def embed(texts: List[str], model: Optional[str] = None) -> Optional[List[List[float]]]:
    """
    Embed texts using the configured mode.
    Returns list of float vectors, or None if all providers fail.
    """
    if not texts:
        return []
    if _use_local():
        return _local_embed(texts, model)

    url = _remote_endpoint()
    if not url:
        # Fall back to local if remote endpoint is not configured but we are in remote mode
        if os.getenv("USE_LOCAL_EMBEDDER", "false").lower() == "true":
            return _local_embed(texts, model)
        return None

    token = _remote_token()
    vecs = _call_remote_embed(url, token, texts, model)
    if vecs and len(vecs) == len(texts):
        return vecs

    if os.getenv("USE_LOCAL_EMBEDDER", "false").lower() == "true":
        return _local_embed(texts, model)
    log.warning("All embed providers failed — caller should degrade gracefully")
    return None
