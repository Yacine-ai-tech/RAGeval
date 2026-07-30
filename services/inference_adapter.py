"""
RAGeval Inference Adapter
==========================
Unified adapter for embedding inference that can't run on the 512MB Render free tier.
Mirrors the IntelAI inference_adapter.py pattern.

Fallback chain (remote mode):
  1. Orchestrator Studio (/embed)        [RAGEVAL_REMOTE_ENDPOINT]
  2. Cohere /v2/embed                    [COHERE_API_KEY]
  3. Jina /v1/embeddings                 [JINA_API_KEY]
  4. Local sentence-transformers          [USE_LOCAL_EMBEDDER=true]
  5. None → caller degrades gracefully

Env vars:
  RAGEVAL_INFERENCE_MODE=local|remote   (default: remote if RAGEVAL_REMOTE_ENDPOINT set)
  RAGEVAL_REMOTE_ENDPOINT=              (Orchestrator tunnel URL — falls back to LIGHTNING_EMBED_URL)
  RAGEVAL_REMOTE_TOKEN=                 (bearer token — falls back to INFERENCE_TOKEN)
  EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
  COHERE_API_KEY=
  JINA_API_KEY=
  HOSTED_EMBEDDING_MODEL=embed-english-v3.0
  HOSTED_EMBED_INPUT_TYPE=search_document
  RAGEVAL_EMBED_TIMEOUT=30
  USE_LOCAL_EMBEDDER=false
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
    return (os.getenv("USE_LOCAL_EMBEDDER", "false").lower() == "true"
            and not _remote_endpoint())


def _fire_wake():
    global _LAST_WAKE
    url = (os.getenv("ORCHESTRATOR_URL", "") or os.getenv("RAGEVAL_REMOTE_ENDPOINT", "")).strip()
    if not url or (time.time() - _LAST_WAKE) < 60:
        return
    _LAST_WAKE = time.time()

    def _go():
        try:
            h = {"Content-Type": "application/json"}
            tk = os.getenv("ORCH_TOKEN", os.getenv("RAGEVAL_REMOTE_TOKEN", "")).strip()
            if tk:
                h["Authorization"] = f"Bearer {tk}"
            body = _json.dumps({"gpu": False, "service": "rageval"}).encode()
            req = urllib.request.Request(url.rstrip("/") + "/wake", data=body, headers=h)
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            log.debug("wake signal failed: %s", e)

    threading.Thread(target=_go, daemon=True).start()


def _orchestrator_embed(texts: List[str], model: Optional[str] = None) -> Optional[List[List[float]]]:
    url = _remote_endpoint()
    if not url:
        return None
    ep = url.lower()
    if "cohere.com" in ep or "jina.ai" in ep:
        return None  # not an orchestrator endpoint
    timeout = int(os.getenv("RAGEVAL_EMBED_TIMEOUT", "30"))
    try:
        payload: dict = {"texts": texts}
        if model:
            payload["model"] = model
        h = {"Content-Type": "application/json"}
        tk = _remote_token()
        if tk:
            h["Authorization"] = f"Bearer {tk}"
        req = urllib.request.Request(url + "/embed", data=_json.dumps(payload).encode(), headers=h)
        resp = _json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        return resp.get("embeddings")
    except Exception as e:
        log.warning("orchestrator embed failed (%s) — waking studio", e)
        _fire_wake()
        return None


def _cohere_embed(texts: List[str]) -> Optional[List[List[float]]]:
    key = os.getenv("COHERE_API_KEY", "").strip()
    if not key:
        return None
    try:
        url = os.getenv("COHERE_BASE_URL", "https://api.cohere.com").rstrip("/") + "/v2/embed"
        payload = {
            "model": os.getenv("HOSTED_EMBEDDING_MODEL", "embed-english-v3.0"),
            "texts": list(texts),
            "input_type": os.getenv("HOSTED_EMBED_INPUT_TYPE", "search_document"),
            "embedding_types": ["float"],
        }
        h = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        req = urllib.request.Request(url, data=_json.dumps(payload).encode(), headers=h)
        data = _json.loads(urllib.request.urlopen(req, timeout=30).read())
        return data["embeddings"]["float"]
    except Exception as e:
        log.warning("cohere embed failed: %s", e)
        return None


def _jina_embed(texts: List[str]) -> Optional[List[List[float]]]:
    key = os.getenv("JINA_API_KEY", "").strip()
    if not key:
        return None
    try:
        url = "https://api.jina.ai/v1/embeddings"
        payload = {"model": os.getenv("HOSTED_EMBEDDING_MODEL", "jina-embeddings-v3"), "input": list(texts)}
        h = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        req = urllib.request.Request(url, data=_json.dumps(payload).encode(), headers=h)
        data = _json.loads(urllib.request.urlopen(req, timeout=30).read())
        return [r["embedding"] for r in sorted(data["data"], key=lambda d: d.get("index", 0))]
    except Exception as e:
        log.warning("jina embed failed: %s", e)
        return None


_local_embedder = None


def _local_embed(texts: List[str], model: Optional[str] = None) -> Optional[List[List[float]]]:
    global _local_embedder
    try:
        from sentence_transformers import SentenceTransformer
        m = model or os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        if _local_embedder is None:
            _local_embedder = SentenceTransformer(m)
        return _local_embedder.encode(texts, normalize_embeddings=True).tolist()
    except Exception as e:
        log.warning("local embed failed: %s", e)
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
    # Remote chain
    vecs = _orchestrator_embed(texts, model)
    if vecs and len(vecs) == len(texts):
        return vecs
    vecs = _cohere_embed(texts)
    if vecs and len(vecs) == len(texts):
        return vecs
    vecs = _jina_embed(texts)
    if vecs and len(vecs) == len(texts):
        return vecs
    if os.getenv("USE_LOCAL_EMBEDDER", "false").lower() == "true":
        return _local_embed(texts, model)
    log.warning("All embed providers failed — caller should degrade gracefully")
    return None
