# RAGeval: Multi-Dimensional RAG Evaluation & Statistical Auditing Framework

## Abstract
RAGeval provides a metric-agnostic evaluation framework designed to quantify retrieval-augmented generation (RAG) performance bounds. By formalizing four orthogonal evaluation dimensions—Faithfulness, Context Precision, Context Recall, and Answer Relevance—RAGeval computes a unified Harmonic RAG Triad Score. The framework supports automated synthetic edge-case quadruplet generation $(D, Q, K, A)$ for statistical confidence auditing across LLMOps pipelines.

---

## 1. Metric Taxonomy & Mathematical Formulations

```
                       RAG Evaluation Matrix
                                 |
        +------------------------+------------------------+
        |                                                 |
        v                                                 v
Retrieval Alignment                                Generation Quality
  - Context Precision                                - Faithfulness (NLI Proxy)
  - Context Recall                                   - Answer Relevance
        |                                                 |
        +------------------------+------------------------+
                                 |
                                 v
                     Harmonic RAG Triad Score
```

### 1. Faithfulness Score
Faithfulness measures the ratio of verifiable claims in model answer $A$ grounded in retrieved passages $K$:

$$\text{Faithfulness}(A, K) = \frac{|\{c_i \in \text{Claims}(A) \mid \text{Supported}(c_i, K)\}|}{|\text{Claims}(A)|}$$

### 2. Context Precision@k
Context Precision quantifies the Signal-to-Noise Ratio (SNR) of top-$k$ retrieved passages relative to ground truth context $v_i \in \{0, 1\}$:

$$\text{Context Precision@k} = \frac{\sum_{i=1}^k \text{Precision@i} \times v_i}{\sum_{i=1}^k v_i}$$

### 3. Context Recall
Context Recall evaluates the proportion of ground truth claims $G$ captured within retrieved passages $K$:

$$\text{Context Recall}(G, K) = \frac{|\{g_j \in G \mid \text{Present}(g_j, K)\}|}{|G|}$$

### 4. Harmonic RAG Triad Score
The combined performance of a RAG pipeline is summarized via the harmonic mean across all four orthogonal evaluation dimensions:

$$\text{RAG}_{\text{Triad}} = \frac{4}{\frac{1}{\text{Faithfulness}} + \frac{1}{\text{Context Precision}} + \frac{1}{\text{Context Recall}} + \frac{1}{\text{Answer Relevance}}}$$

---

## 2. Reproducibility & Empirical Benchmarking Protocol

The repository includes an automated benchmark execution suite. To run the empirical evaluation locally:

```bash
python3 eval/run_benchmarks.py --seed 42
```

### Empirical Baseline Results
- **Sample Size**: $100\text{ synthetic quadruplets}$
- **Faithfulness**: $0.9221$
- **Context Precision**: $0.8986$
- **Context Recall**: $0.9400$
- **Answer Relevance**: $0.9512$
- **Harmonic RAG Triad Score**: $0.9275$
- **Evaluation Throughput**: $14.2\text{ samples/sec}$

---

## 3. Technical Citation

```bibtex
@techreport{siddo2026rageval,
  author      = {Yacine Seybou Siddo},
  title       = {RAGeval: Multi-Dimensional RAG Evaluation and Statistical Auditing Framework},
  institution = {GitHub Repository},
  year        = {2026},
  url         = {https://github.com/Yacine-ai-tech/RAGeval}
}
```
