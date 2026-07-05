"""
RAGEvaluator — Multi-judge consensus + 5 scorers + cost tracking.
"""
from __future__ import annotations

import asyncio
import os
import statistics
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rageval._compat import settings, get_logger  # self-contained (works when pip-installed)

log = get_logger(__name__)

try:
    # NOTE: sentence_transformers pulls in torch (~400MB resident) — importing it at module load
    # OOMs small (512MB) hosts before the app can even serve /health. So we import only the light
    # deps here and defer the heavy SentenceTransformer import into _ensure_embedder() (lazy).
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    _ST = True
except ImportError:
    _ST = False
    log.warning("sklearn / numpy not installed — embedding scorers stub")

try:
    import litellm
    from litellm import acompletion
    # Drop provider-unsupported params instead of erroring — e.g. GPT-5 models reject
    # temperature=0.0 (only 1 is allowed), which otherwise makes the OpenAI judge fail.
    litellm.drop_params = True
    _LITELLM = True
except ImportError:
    _LITELLM = False


# Pricing per 1M tokens (input, output), approximate Mar-2026 values
GROQ_PRICES = {
    "groq/llama-3.3-70b-versatile": (0.59, 0.79),
    "groq/llama-3.1-70b": (0.59, 0.79),
    "groq/llama-3.1-8b": (0.05, 0.08),
    "groq/mixtral-8x7b": (0.24, 0.24),
}
ANTHROPIC_PRICES = {
    "anthropic/claude-sonnet-4-6": (3.00, 15.00),
    "anthropic/claude-haiku-4-5": (1.00, 5.00),
    "anthropic/claude-opus-4-7": (15.00, 75.00),
}
OPENAI_PRICES = {
    "openai/gpt-5": (5.00, 15.00),
    "openai/gpt-5-mini": (0.15, 0.60),
}


class RAGEvaluator:
    """Multi-judge consensus evaluator with cost tracking and persona awareness."""

    def __init__(self, embedding_model: Optional[str] = None):
        self.embedding_model_name = embedding_model or settings.EMBEDDING_MODEL
        self._embedder = None

    def _ensure_embedder(self):
        # Local SentenceTransformer (torch ~400MB resident) is OFF by default: loading it on a
        # 512MB host OOM-crashes the process (the /eval/score 502 we hit). Embedding scorers run
        # via the remote Lightning backend (see _embed); set USE_LOCAL_EMBEDDER=true only where
        # there's RAM headroom.
        if not _ST:
            return None
        if os.getenv("USE_LOCAL_EMBEDDER", "false").strip().lower() not in ("1", "true", "yes", "on"):
            return None
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer  # lazy: torch loads only now
            except ImportError:
                log.warning("sentence-transformers not installed — embedding scorer unavailable")
                return None
            log.info("Loading embedding model: %s", self.embedding_model_name)
            self._embedder = SentenceTransformer(self.embedding_model_name)
        return self._embedder

    _LAST_EMBED_WAKE = 0.0

    def _remote_embed(self, texts: List[str], model: Optional[str] = None):
        """Embed via the Lightning inference backend (LIGHTNING_EMBED_URL) so small (512MB) hosts
        don't OOM loading torch. Sends `model` so the Studio embeds with the requested model (real
        multi-model comparison). Returns a numpy array or None; on failure wakes the Studio."""
        url = os.getenv("LIGHTNING_EMBED_URL", "").strip()
        if not url:
            return None
        try:
            import json as _j, urllib.request
            h = {"Content-Type": "application/json", "User-Agent": "RAGeval/1.0 (+https://ysiddo-ai-projects.app)"}
            tk = os.getenv("INFERENCE_TOKEN", "").strip()
            if tk:
                h["Authorization"] = "Bearer " + tk
            payload = {"texts": texts}
            if model:
                payload["model"] = model
            req = urllib.request.Request(url.rstrip("/") + "/embed", data=_j.dumps(payload).encode(), headers=h)
            vecs = _j.loads(urllib.request.urlopen(req, timeout=float(os.getenv("LIGHTNING_EMBED_TIMEOUT", "30"))).read())["embeddings"]
            return np.asarray(vecs)
        except Exception as e:
            log.warning("remote embed unavailable (%s) — degrading + waking studio", e)
            self._wake_studio()
            return None

    def _wake_studio(self):
        """Fire-and-forget wake of the on-demand inference Studio (rate-limited)."""
        import time as _t, threading
        url = os.getenv("ORCHESTRATOR_URL", "").strip()
        if not url or (_t.time() - RAGEvaluator._LAST_EMBED_WAKE) < 60:
            return
        RAGEvaluator._LAST_EMBED_WAKE = _t.time()
        def _go():
            try:
                import json as _j, urllib.request
                h = {"Content-Type": "application/json", "User-Agent": "RAGeval/1.0 (+https://ysiddo-ai-projects.app)"}
                tk = os.getenv("ORCH_TOKEN", "").strip()
                if tk:
                    h["Authorization"] = "Bearer " + tk
                urllib.request.urlopen(urllib.request.Request(url.rstrip("/") + "/wake",
                    data=_j.dumps({"gpu": False}).encode(), headers=h), timeout=90)
            except Exception:
                pass
        threading.Thread(target=_go, daemon=True).start()

    def _hosted_embed(self, texts: List[str]):
        """Hosted embeddings backstop (Cohere ``/v2/embed`` by default, Jina ``/v1/embeddings``
        alternate) so retrieval scoring stays real when the on-demand Lightning Studio is unreachable
        and torch isn't installed — survives on a 512MB host. Enabled by ``HOSTED_EMBED_PROVIDER``
        (cohere|jina) + the provider's free, no-card key. Returns np.ndarray or None. This is a
        graceful fallback: true multi-model embedding comparison still uses the Studio (this path
        always uses the hosted model, not self.embedding_model_name). Stdlib urllib only."""
        provider = os.getenv("HOSTED_EMBED_PROVIDER", "").strip().lower()
        if provider not in ("cohere", "jina"):
            return None
        key = os.getenv("COHERE_API_KEY" if provider == "cohere" else "JINA_API_KEY", "").strip()
        if not key:
            return None
        try:
            import json as _j, urllib.request
            timeout = float(os.getenv("HOSTED_EMBED_TIMEOUT", "30"))
            h = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
            if provider == "cohere":
                url = os.getenv("COHERE_BASE_URL", "https://api.cohere.com").rstrip("/") + "/v2/embed"
                payload = {"model": os.getenv("HOSTED_EMBEDDING_MODEL", "embed-english-v3.0"),
                           "texts": list(texts),
                           "input_type": os.getenv("HOSTED_EMBED_INPUT_TYPE", "search_document"),
                           "embedding_types": ["float"]}
                req = urllib.request.Request(url, data=_j.dumps(payload).encode(), headers=h)
                data = _j.loads(urllib.request.urlopen(req, timeout=timeout).read())
                vecs = data["embeddings"]["float"]
            else:  # jina (OpenAI-compatible embeddings schema)
                url = "https://api.jina.ai/v1/embeddings"
                payload = {"model": os.getenv("HOSTED_EMBEDDING_MODEL", "jina-embeddings-v3"),
                           "input": list(texts)}
                req = urllib.request.Request(url, data=_j.dumps(payload).encode(), headers=h)
                data = _j.loads(urllib.request.urlopen(req, timeout=timeout).read())
                vecs = [r["embedding"] for r in sorted(data["data"], key=lambda d: d.get("index", 0))]
            return np.asarray(vecs)
        except Exception as e:
            log.warning("hosted embed unavailable (%s) — degrading", e)
            return None

    def _embed(self, texts: List[str]):
        """Embed texts with THIS evaluator's model (self.embedding_model_name): remote Lightning
        backend first (off-box, no OOM), then a hosted API backstop (HOSTED_EMBED_PROVIDER), then a
        local model only if USE_LOCAL_EMBEDDER. Returns a numpy array or None (caller degrades to a
        neutral score)."""
        if not texts:
            return None
        remote = self._remote_embed(texts, model=self.embedding_model_name)
        if remote is not None and len(remote) == len(texts):
            return remote
        # Hosted-API backstop: keeps relevance scoring real when the Studio is down (no torch needed).
        hosted = self._hosted_embed(texts)
        if hosted is not None and len(hosted) == len(texts):
            return hosted
        emb = self._ensure_embedder()
        if emb is None:
            return None
        return np.asarray(emb.encode(texts))

    @staticmethod
    def _tokens(s: str) -> set:
        import re
        return {w for w in re.findall(r"[a-z0-9$%.]+", (s or "").lower()) if len(w) > 1}

    @classmethod
    def _lexical_sim(cls, a: str, b: str) -> float:
        """Overlap coefficient — share of a's tokens covered by b. Stdlib-only fallback
        used when no embedder is reachable, so the scorers stay useful without torch."""
        ta, tb = cls._tokens(a), cls._tokens(b)
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta)

    def score_retrieval_relevance(self, query: str, chunks: List[str]) -> float:
        """Mean cosine(query, retrieved chunks) — embeds off-box via the Lightning backend.
        Falls back to a lexical-overlap score when no embedder is available (so a base
        ``pip install`` returns a meaningful number instead of a silent 0.0)."""
        if not chunks:
            return 0.0
        vecs = self._embed([query] + chunks)
        if vecs is None or len(vecs) != len(chunks) + 1:
            return round(statistics.mean(self._lexical_sim(query, c) for c in chunks), 4)
        sims = cosine_similarity(vecs[:1], vecs[1:])[0]
        return float(np.mean(sims))

    async def _judge_groundedness(self, answer: str, context: str, model: str) -> Optional[float]:
        """One LLM judge call. Returns a float 0-1, or ``None`` when the judge is unavailable
        (LiteLLM missing, or the provider errors — e.g. a model whose API key isn't set). A
        ``None`` judge is SKIPPED by the consensus rather than counted, so an unconfigured judge
        (say OpenAI before you add the key) never pollutes the score or triggers false review flags."""
        if not _LITELLM:
            return None  # judge unavailable → skip (do not inject a fake 0.5)
        try:
            resp = await acompletion(
                model=model,
                messages=[{
                    "role": "user",
                    "content": (
                        "Is this answer fully supported by the context? "
                        "Score 0.0-1.0 (0=hallucinated, 1=fully grounded). "
                        "Return ONLY the float number, nothing else.\n\n"
                        f"Answer: {answer[:2000]}\n\nContext: {context[:4000]}"
                    ),
                }],
                temperature=0.0,
            )
            content = (resp.choices[0].message.content or "").strip()
            # Parse the score: prefer a DECIMAL (0.85 / 1.0) — the actual score format — so we
            # don't grab the leading "0" from prose like "on a 0-1 scale". Fall back to a bare 0/1.
            import re
            m = re.search(r"(?<![.\d])(?:0?\.\d+|1\.0+)(?![.\d])", content) or re.search(r"\b[01]\b", content)
            return max(0.0, min(1.0, float(m.group()))) if m else None
        except Exception as e:
            # Missing API key / provider error → treat as an unavailable judge (skip), not 0.5.
            log.warning("judge %s unavailable (skipped): %s", model, e)
            return None

    async def score_groundedness_consensus(self, answer: str, context: str) -> Dict[str, Any]:
        """Multi-judge consensus across the JUDGE_MODELS that are actually reachable. Judges whose
        provider key isn't configured are skipped, so the score reflects only real votes."""
        scores: List[Dict[str, Any]] = []
        for model in settings.JUDGE_MODELS:
            s = await self._judge_groundedness(answer, context, model=model)
            if s is not None:                       # skip unavailable/unconfigured judges
                scores.append({"model": model, "score": s})
        nums = [s["score"] for s in scores]
        stdev = statistics.stdev(nums) if len(nums) > 1 else 0.0
        return {
            "consensus": statistics.mean(nums) if nums else 0.0,
            "stdev": stdev,
            "judges": scores,
            "judges_used": len(scores),
            # Only flag disagreement when at least two real judges voted.
            "flag_for_review": len(nums) > 1 and stdev > 0.2,
        }

    def score_faithfulness(self, answer: str, chunks: List[str]) -> float:
        """Embedding-similarity NLI proxy: max similarity to any chunk, averaged over sentences.
        Embeds off-box via the Lightning backend (one batched call); 0.0 when unavailable."""
        if not chunks or not answer.strip():
            return 0.0
        sentences = [s.strip() for s in answer.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if not sentences:
            return 0.0
        vecs = self._embed(chunks + sentences)  # one call: [chunks..., sentences...]
        if vecs is None or len(vecs) != len(chunks) + len(sentences):
            # Lexical fallback: mean over sentences of the best token-overlap with any chunk.
            return round(statistics.mean(max(self._lexical_sim(s, c) for c in chunks) for s in sentences), 4)
        chunk_vecs = vecs[:len(chunks)]
        sent_vecs = vecs[len(chunks):]
        sims = cosine_similarity(sent_vecs, chunk_vecs)
        per_sent_max = sims.max(axis=1)
        return float(np.mean(per_sent_max))

    @staticmethod
    def calculate_cost(tokens: int, model: str, input_ratio: float = 0.7) -> float:
        """Estimate USD cost from total tokens (split per input_ratio)."""
        prices = {**GROQ_PRICES, **ANTHROPIC_PRICES, **OPENAI_PRICES}
        if model not in prices:
            return 0.0
        in_price, out_price = prices[model]
        input_toks = tokens * input_ratio
        output_toks = tokens * (1 - input_ratio)
        return (input_toks * in_price + output_toks * out_price) / 1_000_000

    async def score_interaction(
        self,
        query: str,
        answer: str,
        chunks: List[str],
        tokens_used: int,
        latency_ms: float,
        model: str,
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        """End-to-end interaction scoring."""
        relevance = self.score_retrieval_relevance(query, chunks)
        consensus = await self.score_groundedness_consensus(answer, "\n".join(chunks))
        faithfulness = self.score_faithfulness(answer, chunks)
        cost = self.calculate_cost(tokens_used, model)
        groundedness = consensus["consensus"]
        overall_quality = 0.4 * relevance + 0.4 * groundedness + 0.2 * faithfulness

        flags: List[str] = []
        if relevance < 0.5:
            flags.append("LOW_RETRIEVAL_RELEVANCE")
        if groundedness < 0.6:
            flags.append("POTENTIAL_HALLUCINATION")
        if latency_ms > 5000:
            flags.append("HIGH_LATENCY")
        if consensus["flag_for_review"]:
            flags.append("JUDGE_DISAGREEMENT")

        return {
            "relevance": relevance,
            "groundedness": groundedness,
            "groundedness_consensus": consensus,
            "faithfulness": faithfulness,
            "cost_usd": cost,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "model": model,
            "persona": persona,
            "overall_quality": overall_quality,
            "flags": flags,
            "needs_review": bool(flags),
        }
