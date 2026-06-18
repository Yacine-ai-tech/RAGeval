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
    from litellm import acompletion
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
        if not _ST:
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

    def _remote_embed(self, texts: List[str]):
        """Embed via the Lightning inference backend (LIGHTNING_EMBED_URL) so small (512MB) hosts
        don't OOM loading torch. Returns a numpy array or None (caller falls back to local)."""
        import os
        url = os.getenv("LIGHTNING_EMBED_URL", "").strip()
        if not url:
            return None
        try:
            import json as _j, urllib.request
            h = {"Content-Type": "application/json", "User-Agent": "RAGeval/1.0 (+https://ysiddo-ai-projects.app)"}
            tk = os.getenv("INFERENCE_TOKEN", "").strip()
            if tk:
                h["Authorization"] = "Bearer " + tk
            req = urllib.request.Request(url.rstrip("/") + "/embed", data=_j.dumps({"texts": texts}).encode(), headers=h)
            vecs = _j.loads(urllib.request.urlopen(req, timeout=float(os.getenv("LIGHTNING_EMBED_TIMEOUT", "30"))).read())["embeddings"]
            return np.asarray(vecs)
        except Exception as e:
            log.warning("remote embed unavailable (%s) — local fallback", e)
            return None

    def score_retrieval_relevance(self, query: str, chunks: List[str]) -> float:
        """Cosine similarity between query and retrieved chunks (mean). Uses the remote Lightning
        embedder when configured (off-box, no OOM); else the local model."""
        if not chunks:
            return 0.0
        remote = self._remote_embed([query] + chunks)
        if remote is not None and len(remote) == len(chunks) + 1:
            sims = cosine_similarity(remote[:1], remote[1:])[0]
            return float(np.mean(sims))
        emb = self._ensure_embedder()
        if emb is None:
            return 0.0
        q_vec = emb.encode([query])
        c_vec = emb.encode(chunks)
        sims = cosine_similarity(q_vec, c_vec)[0]
        return float(np.mean(sims))

    async def _judge_groundedness(self, answer: str, context: str, model: str) -> float:
        """One LLM judge call. Returns float 0-1."""
        if not _LITELLM:
            return 0.5  # stub
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
            content = (resp.choices[0].message.content or "0.5").strip()
            # Extract the first float in the response
            import re
            m = re.search(r"[01]?\.\d+|\d", content)
            return float(m.group()) if m else 0.5
        except Exception as e:
            log.warning("judge %s failed: %s", model, e)
            return 0.5

    async def score_groundedness_consensus(self, answer: str, context: str) -> Dict[str, Any]:
        """Multi-judge consensus across configured JUDGE_MODELS."""
        scores: List[Dict[str, Any]] = []
        for model in settings.JUDGE_MODELS:
            s = await self._judge_groundedness(answer, context, model=model)
            scores.append({"model": model, "score": s})
        nums = [s["score"] for s in scores]
        stdev = statistics.stdev(nums) if len(nums) > 1 else 0.0
        return {
            "consensus": statistics.mean(nums) if nums else 0.0,
            "stdev": stdev,
            "judges": scores,
            "flag_for_review": stdev > 0.2,
        }

    def score_faithfulness(self, answer: str, chunks: List[str]) -> float:
        """Embedding-similarity NLI proxy: max similarity to any chunk, averaged over sentences."""
        if not chunks or not answer.strip():
            return 0.0
        emb = self._ensure_embedder()
        if emb is None:
            return 0.0
        sentences = [s.strip() for s in answer.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if not sentences:
            return 0.0
        chunk_vecs = emb.encode(chunks)
        sent_vecs = emb.encode(sentences)
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
