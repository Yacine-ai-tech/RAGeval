import React from 'react';
import {
  FlaskConical, Gauge, Award, Layers, Scale, ShieldCheck,
  CheckCircle2, Terminal, BookOpen, ExternalLink, Cpu,
  BarChart3, AlertTriangle, Users
} from 'lucide-react';
import { PageHeader } from '../kit/AppShell';
import { Card, Button } from '../kit/primitives';
import { Link } from 'react-router-dom';

export default function ResearchPage() {
  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto space-y-8">
      <PageHeader
        title="RAGeval — LLMOps & Judge-Consensus Research"
        sub="Theoretical foundations of LLM-as-a-judge evaluation, multi-model consensus, correlated error dynamics, and entailment scoring."
        actions={
          <div className="flex gap-2">
            <Link to="/benchmark">
              <Button variant="primary">
                <Award size={14} className="mr-1 inline" /> View Benchmarks
              </Button>
            </Link>
            <Link to="/user-guide">
              <Button variant="secondary">
                <BookOpen size={14} className="mr-1 inline" /> User Guide
              </Button>
            </Link>
          </div>
        }
      />

      {/* Abstract */}
      <Card title="Abstract & Architectural Focus" className="bg-surface/80">
        <p className="text-dim leading-relaxed text-sm mb-4">
          RAGeval is an open-source evaluation and observability platform for retrieval-augmented generation. It replaces brittle, uncalibrated single-model heuristics with a multi-judge groundedness panel. The core design principles address documented failure modes of LLM-as-a-judge systems: verbosity bias, self-preference, and correlated errors across frontier model families.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="rounded-xl border border-line bg-surface-2 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-accent mb-1">Entailment Logic</div>
            <div className="font-semibold text-body text-sm mb-1">Reasoning over Similarity</div>
            <div className="text-xs text-dim">Embedding cosine similarity measures topical proximity; LLM judges evaluate logical consistency and factual entailment.</div>
          </div>
          <div className="rounded-xl border border-line bg-surface-2 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-ok mb-1">Judge Jury</div>
            <div className="font-semibold text-body text-sm mb-1">Heterogeneous Panel</div>
            <div className="text-xs text-dim">4 distinct model families (Claude, Groq/Llama, GPT, Gemini) scoring each turn without single-model SPOF.</div>
          </div>
          <div className="rounded-xl border border-line bg-surface-2 p-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">Uncertainty Signal</div>
            <div className="font-semibold text-body text-sm mb-1">Variance-Driven Review</div>
            <div className="text-xs text-dim">Inter-judge disagreement (σ) triggers human-in-the-loop review, surfacing subtle hallucinations.</div>
          </div>
        </div>
      </Card>

      {/* 1. Why LLM Judge over Embedding Similarity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="1. Logical Entailment vs Topical Similarity">
          <div className="space-y-3 text-xs text-dim leading-relaxed">
            <p>
              Cosine similarity over dense embeddings is a common low-cost heuristic for RAG retrieval relevance, but fails as a factual grounding metric:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li><strong className="text-body">Inverted Truth:</strong> An answer asserting "Revenue decreased by 15%" embeds in close cosine proximity to a source stating "Revenue increased by 15%", completely missing the contradiction.</li>
              <li><strong className="text-body">Paraphrase Penalties:</strong> A faithful, highly synthesised response using varied vocabulary receives an artificially lower cosine score than an ungrounded direct string copy.</li>
            </ul>
            <p>
              RAGeval therefore employs full reasoning LLMs to explicitly audit directional entailment: whether every claim in the generated answer is entailed by the retrieved context.
            </p>
          </div>
        </Card>

        {/* 2. Bias Mitigation */}
        <Card title="2. Mitigating Single-Judge Failure Modes">
          <div className="space-y-3 text-xs text-dim leading-relaxed">
            <p>
              Single-judge LLM grading carries documented cognitive and statistical biases:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li><strong className="text-body">Verbosity Bias:</strong> Tendency to award higher scores to wordy or lengthy responses independent of factual accuracy.</li>
              <li><strong className="text-body">Self-Preference Bias:</strong> Preferring token generation patterns and rhetorical stylings produced by the judge's own architecture.</li>
              <li><strong className="text-body">Position Bias:</strong> Favoring earlier context chunks or candidate options during pairwise assessment.</li>
            </ul>
            <p>
              A heterogeneous panel distributing evaluation across independent architectures dampens family-specific idiosyncrasies and produces calibrated confidence intervals.
            </p>
          </div>
        </Card>
      </div>

      {/* 3. Panel Dynamics & Correlated Errors */}
      <Card title="3. Correlated Errors & Panel Aggregation Dynamics">
        <div className="space-y-4 text-sm text-dim leading-relaxed">
          <p>
            Recent empirical literature (Kohli, 2026; Acharya et al., Amazon 2026) reveals that ensembling frontier language models does not yield independent Gaussian noise reduction:
          </p>
          <div className="rounded-xl border border-line bg-surface-2 p-4 text-xs space-y-2">
            <div className="font-semibold text-body">The "Two Effective Votes" Phenomenon (Kohli, arXiv:2605.29800)</div>
            <p>
              Across nine frontier LLMs evaluated on hallucination benchmarks, error correlation between models remains above 0.65. Consequently, naive uniform averaging can allow weaker judges to drag down a superior judge's verdict.
            </p>
          </div>
          <p className="text-xs">
            RAGeval formalizes this dynamic in <code className="text-accent">RAGEvaluator.score_groundedness_consensus()</code> via two calibrated strategies:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="rounded-lg bg-surface-2 p-3 border border-line">
              <div className="font-semibold text-body mb-1">Accuracy-Weighted Consensus</div>
              <div>Judges are weighted dynamically by their empirical accuracy on calibrated benchmark splits (Li et al., HaluEval-QA), preventing weaker models from skewing the final consensus score.</div>
            </div>
            <div className="rounded-lg bg-surface-2 p-3 border border-line">
              <div className="font-semibold text-body mb-1">Disagreement-Gated Escalation</div>
              <div>When inter-judge standard deviation exceeds σ &gt; 0.20, the system flags the turn for asynchronous arbitration or escalation rather than masking the uncertainty in a blended mean.</div>
            </div>
          </div>
        </div>
      </Card>

      {/* 4. The 4-Judge Primary Panel */}
      <Card title="4. Four-Judge Architecture Specification">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="rounded-lg bg-surface-2 p-3 border border-line">
            <div className="font-semibold text-body mb-1">Gemini 3.5 Flash</div>
            <div className="text-accent font-bold mb-1">Accuracy: 88.5%</div>
            <div className="text-dim">Highest individual judge accuracy on HaluEval-QA. Excels at numerical precision and negation tracking.</div>
          </div>
          <div className="rounded-lg bg-surface-2 p-3 border border-line">
            <div className="font-semibold text-body mb-1">GPT-5-mini</div>
            <div className="text-accent font-bold mb-1">Accuracy: 86.0%</div>
            <div className="text-dim">Robust reasoning baseline with high recall (0.950). Catches subtle hallucinations across extended texts.</div>
          </div>
          <div className="rounded-lg bg-surface-2 p-3 border border-line">
            <div className="font-semibold text-body mb-1">Groq gpt-oss-120b</div>
            <div className="text-accent font-bold mb-1">Accuracy: 83.5%</div>
            <div className="text-dim">Ultra-fast open-weight reasoning model providing independent non-proprietary judgment signal.</div>
          </div>
          <div className="rounded-lg bg-surface-2 p-3 border border-line">
            <div className="font-semibold text-body mb-1">Claude Haiku 4.5</div>
            <div className="text-accent font-bold mb-1">Accuracy: 75.0%</div>
            <div className="text-dim">Fast, cost-efficient reasoning judge evaluating concise structural entailment constraints.</div>
          </div>
        </div>
      </Card>

      {/* Academic Citations */}
      <Card title="5. Literature & Reference Works">
        <div className="space-y-3 text-xs text-dim">
          <div className="border-b border-line pb-2">
            <div className="font-semibold text-body">HaluEval: A Large-Scale Hallucination Evaluation Benchmark for Large Language Models</div>
            <div className="text-muted">Li, J., et al. (EMNLP 2023). Standard QA benchmark dataset for evaluating factual consistency.</div>
          </div>
          <div className="border-b border-line pb-2">
            <div className="font-semibold text-body">Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM Evaluation Panels</div>
            <div className="text-muted">Kohli, N. (arXiv:2605.29800, 2026). Mathematical proof of correlated error limits in multi-model juries.</div>
          </div>
          <div className="border-b border-line pb-2">
            <div className="font-semibold text-body">RoPoLL: Robust Panel of LLM Judges via Geometric Median Aggregation</div>
            <div className="text-muted">Acharya, A., et al. (Amazon Science, arXiv:2606.30931, 2026). Formulates breakdown-point 1/2 consensus metrics.</div>
          </div>
          <div>
            <div className="font-semibold text-body">Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena</div>
            <div className="text-muted">Zheng, L., et al. (NeurIPS 2023). Foundational taxonomy of LLM judge bias modes.</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
