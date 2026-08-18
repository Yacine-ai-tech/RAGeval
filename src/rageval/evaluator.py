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


# Multi-judge consensus requires at least this many configured judges — a single judge
# isn't consensus, and RAGeval never substitutes one judge for another as a fallback.
MIN_JUDGES_REQUIRED = 2


class InsufficientJudgesError(RuntimeError):
    """Raised when fewer than MIN_JUDGES_REQUIRED LLM judges are configured/reachable."""


# Pricing per 1M tokens (input, output), approximate Mar-2026 values
GROQ_PRICES = {
    "groq/openai/gpt-oss-120b": (0.59, 0.79),
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
    # gpt-4o-mini is the default configured judge model.
    # gpt-5/gpt-5-mini kept for forward-compat when the key is available.
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-5": (5.00, 15.00),
    "openai/gpt-5-mini": (0.15, 0.60),
}

# ── Persona scope awareness ──────────────────────────────────────────────────
# Which business domains each persona is allowed to speak to. Used to catch when,
# e.g., a CFO response surfaces People/HR figures it shouldn't. Personas not listed
# here are treated as unrestricted (no scope flag).
PERSONA_DOMAINS: Dict[str, set] = {
    "cfo": {"finance", "growth"},
    "chro": {"people", "esg"},
    "hr": {"people", "esg"},
    "cto": {"it", "operations", "finance"},
    "coo": {"operations", "logistics", "growth", "people"},
    "esg": {"esg", "operations", "people"},
    "risk": {"finance", "operations", "esg", "it"},
    "ceo": {"finance", "growth", "operations", "people", "esg", "it", "logistics"},
}
# Signature terms that mark a piece of content as belonging to a business domain.
DOMAIN_TERMS: Dict[str, tuple] = {
    "finance": ("revenue", "margin", "gross margin", "ebitda", "cash runway", "burn rate",
                "profit", "net income", "arr", "mrr", "cash flow", "opex", "capex"),
    "people": ("headcount", "attrition", "turnover", "hiring", "recruit", "absenteeism",
               "employee", "training completion", "engagement score", "payroll"),
    "it": ("uptime", "incident", "deployment frequency", "mttr", "vulnerabilit",
           "security posture", "latency", "sla", "ticket"),
    "operations": ("throughput", "defect rate", "oee", "production", "quality", "safety incident"),
    "logistics": ("inventory", "shipment", "on-time delivery", "supplier", "lead time", "stockout"),
    "esg": ("emissions", "co2", "carbon", "diversity", "sustainability", "governance score"),
    "growth": ("cac", "ltv", "conversion rate", "churn", "nrr", "pipeline", "win rate"),
}


class RAGEvaluator:
    """Multi-judge consensus evaluator with cost tracking and persona awareness."""

    def __init__(self, embedding_model: Optional[str] = None):
        self.embedding_model_name = embedding_model or settings.EMBEDDING_MODEL
        self._embedder = None

    def _ensure_embedder(self):
        # Local SentenceTransformer (torch ~400MB resident) is OFF by default: loading it on a
        # 512MB host OOM-crashes the process (the /eval/score 502 we hit). Embedding scorers run
        # via the remote inference backend (see _embed); set USE_LOCAL_EMBEDDER=true only where
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

    def _remote_embed(self, texts: List[str], model: Optional[str] = None):
        """Embed via a remote inference endpoint (EMBEDDING_ENDPOINT), provider-agnostic."""
        if os.getenv("INFERENCE_MODE", "").strip().lower() != "remote":
            return None

        url = os.getenv("EMBEDDING_ENDPOINT", "").strip()
        if not url:
            return None

        try:
            import httpx
            h = {"Content-Type": "application/json", "User-Agent": "RAGeval/1.0"}
            tk = os.getenv("INFERENCE_TOKEN", "").strip()
            if tk:
                h["Authorization"] = "Bearer " + tk

            timeout = float(os.getenv("EMBED_TIMEOUT", "30"))
            with httpx.Client(timeout=timeout) as client:
                if "huggingface.co" in url:
                    resp = client.post(url, json={"inputs": texts}, headers=h)
                    resp.raise_for_status()
                    arr = np.asarray(resp.json(), dtype=float)
                    if arr.ndim == 3:  # per-token vectors from a plain feature-extraction
                        arr = arr.mean(axis=1)  # pipeline (not a sentence-embedding model) — mean-pool
                    return arr

                payload = {"texts": texts}
                if model:
                    payload["model"] = model
                resp = client.post(url.rstrip("/") + "/embed", json=payload, headers=h)
                resp.raise_for_status()
                vecs = resp.json()["embeddings"]
                return np.asarray(vecs)
        except Exception as e:
            log.warning("remote embed unavailable (%s)", e)
            return None

    def _embed(self, texts: List[str]):
        """Embed texts — remote endpoint first, then local model if USE_LOCAL_EMBEDDER is set."""
        if not texts:
            return None
        remote = self._remote_embed(texts, model=self.embedding_model_name)
        if remote is not None and len(remote) == len(texts):
            return remote
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
        """Overlap coefficient — share of a's tokens covered by b."""
        ta, tb = cls._tokens(a), cls._tokens(b)
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta)

    def score_retrieval_relevance(self, query: str, chunks: List[str]) -> float:
        """Mean cosine(query, retrieved chunks). Falls back to lexical overlap."""
        if not chunks:
            return 0.0
        vecs = self._embed([query] + chunks)
        if vecs is None or len(vecs) != len(chunks) + 1:
            return round(statistics.mean(self._lexical_sim(query, c) for c in chunks), 4)
        sims = cosine_similarity(vecs[:1], vecs[1:])[0]
        return float(np.mean(sims))

    @staticmethod
    def score_ranking(
        ranked_chunks: List[str],
        relevant_chunks: List[str],
        precision_k: int = 5,
        recall_k: int = 10,
    ) -> Dict[str, float]:
        """Standard IR ranking metrics for one query, against labeled ground truth.

        ``ranked_chunks`` is the retrieved chunk texts in rank order (best first);
        ``relevant_chunks`` is the ground-truth set of chunk texts that should have been
        retrieved for this query. Relevance is exact-text membership — the same
        chunk-text-as-identity convention the rest of this API already uses (chunks are
        plain strings everywhere else too), so no separate chunk-ID scheme is needed.

        Unlike ``score_retrieval_relevance`` (embedding similarity, needs no labels),
        precision/recall/MRR require this ground truth and measure something different:
        whether the *actually relevant* documents were retrieved and ranked highly, not
        just whether retrieved text is topically close to the query.
        """
        relevant_set = set(relevant_chunks)
        if not relevant_set:
            return {"precision_at_k": 0.0, "recall_at_k": 0.0, "reciprocal_rank": 0.0}

        top_p = ranked_chunks[:precision_k] if precision_k > 0 else []
        precision_at_k = (
            sum(1 for c in top_p if c in relevant_set) / precision_k if precision_k > 0 else 0.0
        )

        top_r = ranked_chunks[:recall_k] if recall_k > 0 else []
        recall_at_k = sum(1 for c in top_r if c in relevant_set) / len(relevant_set)

        reciprocal_rank = 0.0
        for i, c in enumerate(ranked_chunks, start=1):
            if c in relevant_set:
                reciprocal_rank = 1.0 / i
                break

        return {
            "precision_at_k": precision_at_k,
            "recall_at_k": recall_at_k,
            "reciprocal_rank": reciprocal_rank,
        }

    async def _judge_groundedness(self, answer: str, context: str, model: str) -> Optional[float]:
        """One LLM judge call. Returns a float 0-1, or ``None`` when the judge is unavailable."""
        prompt = (
            "Is this answer fully supported by the context? "
            "Score 0.0-1.0 (0=hallucinated, 1=fully grounded). "
            "Return ONLY the float number, nothing else.\n\n"
            f"Answer: {answer[:2000]}\n\nContext: {context[:4000]}"
        )

        # Hard timeout per judge — a hung call with no timeout stalled a 30-case eval run for
        # ~9h wall-clock before being noticed. asyncio.wait_for() gives every judge call the
        # same ceiling a slow/unresponsive provider can't exceed.
        judge_timeout = float(os.getenv("JUDGE_TIMEOUT", "30"))

        if model.startswith("gemini/"):
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(http_options={"api_version": "v1beta"})
                actual_model = model.split("gemini/", 1)[-1]

                resp = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=actual_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.0)
                    ),
                    timeout=judge_timeout,
                )
                content = (resp.text or "").strip()
            except ImportError:
                log.warning("google-genai not installed, skipping gemini judge")
                return None
            except Exception as e:
                log.warning("gemini judge %s unavailable (skipped): %s", model, e)
                return None
        else:
            if not _LITELLM:
                return None
            try:
                resp = await asyncio.wait_for(
                    acompletion(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                    ),
                    timeout=judge_timeout,
                )
                content = (resp.choices[0].message.content or "").strip()
            except Exception as e:
                log.warning("judge %s unavailable (skipped): %s", model, e)
                return None

        # Parse the score — strip the prompt's own wording before scanning for a number
        import re
        clean = content.replace("0.0-1.0", "").replace("0=hallucinated", "").replace("1=fully grounded", "")
        m = re.search(r"(?<![.\d])(?:0?\.\d+|1\.0+)(?![.\d])", clean) or re.search(r"\b[01]\b", clean)
        return max(0.0, min(1.0, float(m.group()))) if m else None

    async def score_groundedness_consensus(self, answer: str, context: str) -> Dict[str, Any]:
        """Multi-judge consensus across the configured JUDGE_MODELS."""
        if len(settings.JUDGE_MODELS) < MIN_JUDGES_REQUIRED:
            raise InsufficientJudgesError(
                f"RAGeval requires at least {MIN_JUDGES_REQUIRED} configured LLM judges "
                f"(JUDGE_MODELS lists {len(settings.JUDGE_MODELS)}: {settings.JUDGE_MODELS}). "
                "Set JUDGE_MODELS to two or more of the supported providers "
                "(anthropic/..., groq/..., gemini/..., openai/...)."
            )

        async def _run_judge(model):
            s = await self._judge_groundedness(answer, context, model=model)
            if s is not None:
                return {"model": model, "score": s}
            return None

        results = await asyncio.gather(*[_run_judge(model) for model in settings.JUDGE_MODELS])
        scores = [r for r in results if r is not None]

        if len(scores) < MIN_JUDGES_REQUIRED:
            attempted = ", ".join(settings.JUDGE_MODELS)
            raise InsufficientJudgesError(
                f"Only {len(scores)} of {len(settings.JUDGE_MODELS)} configured judges "
                f"responded (need at least {MIN_JUDGES_REQUIRED}). No fallback between "
                f"judges — check API keys/connectivity for: {attempted}"
            )

        nums = [s["score"] for s in scores]
        stdev = statistics.stdev(nums) if len(nums) > 1 else 0.0
        return {
            "consensus": statistics.mean(nums),
            "stdev": stdev,
            "judges": scores,
            "judges_used": len(scores),
            "flag_for_review": stdev > 0.2,
        }

    def score_faithfulness(self, answer: str, chunks: List[str]) -> float:
        """Embedding-similarity NLI proxy: max similarity to any chunk, averaged over sentences.

        Sentence splitting uses a regex that respects decimal numbers (e.g. $4.2M,
        3.14%) and does not split on dots that are surrounded by digits.
        """
        if not chunks or not answer.strip():
            return 0.0
        import re
        # Split on sentence-ending punctuation followed by whitespace, but NOT on
        # dots that are surrounded by digits (e.g. $4.2M, version 1.0, 3.14%).
        sentences = [
            s.strip()
            for s in re.split(r"(?<![0-9])(?<=[.!?])\s+|(?<=[.!?])\s+(?![0-9])", answer)
            if s.strip()
        ]
        # Fallback: if regex produced no splits just use the whole answer as one sentence.
        if not sentences:
            sentences = [answer.strip()]
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
        """Estimate USD cost from total tokens (split per input_ratio).

        `model` here is caller-supplied (LogRequest/ScoreRequest.model describes whatever
        pipeline produced the answer being scored, not one of the fixed JUDGE_MODELS), so it
        isn't guaranteed to arrive in this table's "provider/model" form — a caller reasonably
        passes the bare name their own SDK uses, e.g. "gpt-4o" instead of "openai/gpt-4o". Every
        real query was landing here as a silent $0.0000, indistinguishable from a genuinely free
        call, because of this exact-match requirement. Try the bare name under each known
        provider prefix, and the reverse (strip a prefix the caller did include), before giving
        up and reporting $0.
        """
        prices = {**GROQ_PRICES, **ANTHROPIC_PRICES, **OPENAI_PRICES}
        resolved = prices.get(model)
        if resolved is None and "/" not in model:
            for prefix in ("openai/", "anthropic/", "groq/"):
                resolved = prices.get(prefix + model)
                if resolved is not None:
                    break
        if resolved is None and "/" in model:
            resolved = prices.get(model.rsplit("/", 1)[-1])
        if resolved is None:
            return 0.0
        in_price, out_price = resolved
        input_toks = tokens * input_ratio
        output_toks = tokens * (1 - input_ratio)
        return (input_toks * in_price + output_toks * out_price) / 1_000_000

    @staticmethod
    def _persona_scope_flags(answer: str, persona: Optional[str]) -> List[str]:
        """Persona awareness: return out-of-scope business domains a persona's answer surfaced.

        Only splits on sentence-ending punctuation followed by whitespace — bare
        newlines (e.g. bullet lists) are not treated as sentence boundaries, which
        would otherwise cause false-positive PERSONA_SCOPE_VIOLATION flags.
        """
        if not persona or not answer:
            return []
        allowed = PERSONA_DOMAINS.get(persona.strip().lower())
        if not allowed:
            return []
        import re
        offending: set = set()
        # Split only on ./?/! followed by whitespace — NOT on bare newlines.
        for sent in re.split(r"(?<=[.!?])\s+", answer):
            s = sent.lower()
            if not re.search(r"\d", s):  # no figure -> a mention, not a data pull
                continue
            for dom, terms in DOMAIN_TERMS.items():
                if dom in allowed:
                    continue
                if any(term in s for term in terms):
                    offending.add(dom)
        return sorted(offending)

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
        """End-to-end interaction scoring.

        Uses return_exceptions=True so an InsufficientJudgesError from consensus_task
        does not cancel the still-running relevance/faithfulness threads
        (asyncio.to_thread tasks cannot actually be cancelled — they would otherwise
        keep running with their results silently discarded, wasting embedding API
        quota).
        """
        relevance_task = asyncio.to_thread(self.score_retrieval_relevance, query, chunks)
        consensus_task = self.score_groundedness_consensus(answer, "\n".join(chunks))
        faithfulness_task = asyncio.to_thread(self.score_faithfulness, answer, chunks)

        # return_exceptions=True lets all three tasks run to completion.
        # We then re-raise any InsufficientJudgesError after collecting all results.
        results = await asyncio.gather(
            relevance_task, consensus_task, faithfulness_task,
            return_exceptions=True,
        )
        relevance, consensus, faithfulness = results

        # Re-raise judge errors — don't silently swallow them.
        if isinstance(relevance, BaseException):
            raise relevance
        if isinstance(consensus, BaseException):
            raise consensus
        if isinstance(faithfulness, BaseException):
            raise faithfulness

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

        scope_violations = self._persona_scope_flags(answer, persona)
        if scope_violations:
            flags.append("PERSONA_SCOPE_VIOLATION")

        # Query embedding for pgvector storage (Postgres production tier only).
        query_embedding: Optional[List[float]] = None
        if settings.POSTGRES_URL:
            vecs = await asyncio.to_thread(self._embed, [query])
            if vecs is not None and len(vecs) == 1:
                query_embedding = [float(x) for x in vecs[0]]

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
            "persona_scope_violations": scope_violations,
            "overall_quality": overall_quality,
            "flags": flags,
            "needs_review": bool(flags),
            "query_embedding": query_embedding,
        }
