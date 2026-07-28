## 📋 Table of Contents

- [🌵 What is CactusFruit?](#what-is-cactusfruit)
  - [💻 Performance Benchmarks](#performance-benchmarks)
  - [🚀 Roadmap & Milestones](#roadmap--milestones)
- [🎮 Get Started](#get-started)
- [⚡ Pipeline Architecture](#pipeline-architecture)
  - [Phase 0: Knowledge Base (for grounding)](#phase-0)
  - [Phase 1: Fact Extraction](#phase-1)
  - [Phase 2: Query Generation](#phase-2)
  - [Phase 3: Dual-Path RAG Retrieval](#phase-3)
  - [Phase 4: Cross-Encoder Re-Ranking](#phase-4)
  - [Phase 5: Fact Judging](#phase-5)
  - [Phase 6 & 7: Verification & Decision Logic](#phase-6-7)
- [🛠 Model Zoo](#model-zoo)

---

<a id="what-is-cactusfruit"></a>
## 🌵 What is CactusFruit?

Most teams only evaluate a tiny fraction (<1%) of production AI traffic because running LLMs as evaluators is too slow and expensive. This creates huge blind spots in production.

**CactusFruit enables 100% full-coverage deep evals on all live traffic.**

By orchestrating lightweight, specialized small models (SLMs) with a memory-efficient runtime, CactusFruit can deliver continuous, deep evaluations at scale.

---

<a id="performance-benchmarks"></a>
### 💻 Performance Benchmarks

CactusFruit is engineered to eliminate heavy dependencies by keeping hardware overhead strictly below **4GB RAM / VRAM**.

The entire multi-stage pipeline can even run locally on entry-level consumer hardware. It relies on:

* **Sequential Model Pooling:** To maintain a strict `< 4GB` hardware footprint, models are loaded and executed sequentially with memory garbage collection between phases, ensuring zero out-of-memory errors on 8GB unified memory systems.

* **Persistent Context Objects:** Context objects are retained across model executions when needed, avoiding redundant reconstruction and enabling efficient handoffs between specialized models.

#### Benchmark Baseline: Apple M1 MacBook Air (2020)

* **RAM / VRAM Footprint:** `< 3.8 GB` peak usage across the entire pipeline.
* **Architecture Support:** Runs on Apple Silicon (Metal API) via quantized `llama.cpp` / GGUF binaries without swapping or thermal throttling.
* **Inference Pipeline Profile:**

| Pipeline Stage | Model / Tool | Execution Mode | Memory Overhead |
| --- | --- | --- | --- |
| **Phase 1: Fact Extraction** | `fact-extractor-1.7b` | GGUF `Q8_0` (Metal Acceleration) | ~1.8 GB |
| **Phase 2: Query Generation** | `query-generator-1.5b` | GGUF `Q8_0` (Metal Acceleration) | ~1.6 GB |
| **Phase 3: Hybrid Retrieval** | BM25 + `all-MiniLM-L6-v2` | Tokenizer + In-Memory Vector Search | ~150 MB |
| **Phase 4: Re-Ranking** | `ms-marco-MiniLM-L6-v2` | SafeTensors PyTorch / ONNX | ~180 MB |
| **Phase 5: Fact Judging** | `fact-judge-1.7b` | GGUF `Q8_0` (Sequential Model Load) | ~1.8 GB |

---

<a id="roadmap--milestones"></a>
### 🚀 Roadmap & Milestones

- [x] **SLM Model Fine-Tuning & Model Zoo:** Trained and quantized specialized small models (`fact-extractor-1.7b`, `query-generator-1.5b`, `fact-judge-1.7b`) optimized for granular evaluation tasks.
- [x] **End-to-End Local Pipeline:** Built and validated the complete 7-stage orchestration flow, confirming full functional execution under strict local hardware boundaries.
- [x] **Custom `llama.cpp` Server:** Engineered custom server runtime featuring context retention and model memory pooling optimizations to maintain a `< 4GB` hardware footprint.
- [~] **AWS Cloud Infrastructure Build (~60% Complete):** Scaling up cloud deployment pipelines for hosted, high-throughput batch evaluation. *(See `demo/prod`).*
- [ ] **Model Iteration & Optimization:** Training next-generation, higher-accuracy SLM models for complex reasoning and edge-case fact judging.
- [ ] **Custom `llama.cpp` Server Integration:** Wiring the optimized server directly into the main execution pipeline to replace fallback bindings on local versions.

---

<a id="get-started"></a>
## 🎮 Get Started

Deploy CactusFruit service containers using the unified `deploy.sh` script.

### Prerequisites

* **Docker Engine** (running with build permissions)
* **AWS CLI v2** (configured for STS and ECR)
* **Python 3.x** (for parsing configuration files)

---

### Step 1: Configuration

`deploy.sh` requires two JSON configurations in your root directory:
* `models.json`: Defines model assets and module types.
* `deploy-to.json`: Defines target AWS IAM roles and deployment regions.

> 💡 **Auto-Setup:** If `deploy-to.json` is missing, running `./deploy.sh` will prompt for your AWS IAM Role ARN and generate it automatically.

---

### Step 2: Deployment Commands

Make `deploy.sh` executable:
```bash
chmod +x deploy.sh
```

**Build & Push All Modules:**
```bash
./deploy.sh --build --push --all-modules
```


**Build Specific Modules (Clean Cache):**
```bash
./deploy.sh --build --modules pipeline embedder --purge-docker
```


**Deploy to Custom Profile:**
```bash
./deploy.sh --build --push --all-modules --profile production
```

---

### Step 3: CLI Reference

```text
Usage: ./deploy.sh [OPTIONS]

Options:
  --modules [names...]  Target specific modules (e.g., pipeline embedder reranker)
  --all-modules         Select all modules from models.json plus 'pipeline'
  --profile [name]      Deployment profile from deploy-to.json (default: "default")
  --build               Build Docker images
  --push                Authenticate and push images to AWS ECR
  --purge-docker        Purge Docker build cache before processing
  -h, --help            Show help message
```


---

<a id="pipeline-architecture"></a>
## ⚡ Pipeline Architecture

<a id="phase-0"></a>
### Phase 0: Knowledge Base (for grounding)

This setup is intended for local demos only. For production or broader usage, you'll probably want to connect it to your own knowledge stack.

* **Input:** Raw documents (`.pdf`, `.docx`, `.txt`).
* **Processing:** Parsed via `docling` and chunked into roughly **3-sentence blocks**.
* **Storage:** Extracted chunks store metadata (`source_name`, `source_link`, etc).

---

<a id="phase-1"></a>
### Phase 1: Fact Extraction

Deconstructs target text into atomic claims using a 3-sentence context window.


```

[Prev Sentence] + [Target Sentence] + [Next Sentence]
                          │
                          ▼
               Model: fact-extractor-1.7b
                          │
                          ▼
        ["Atomic Fact 1", "Atomic Fact 2", ...]
```

> `fact-extractor-1.7b` is trained on surrounding sentences to resolve pronouns (like "it" or "he") while preserving the core claim.

> **TODO:** Deduplicate overlapping facts using cosine similarity ($\ge 0.85$).

<details>

<summary>View Sample ChatML</summary>

```xml
<!-- Sample fact-extractor-1.7b ChatML -->
<|im_start|>system
Extract atomic facts from the target.<|im_end|>
<|im_start|>user
Previous: The cat sat on the mat.
Target: It was a sunny day, and the cat felt warm.
Next: Soon, the cat fell asleep.<|im_end|>
<|im_start|>assistant
<think> The target mentions the weather and the cat's physical state. </think>
<fact> It was a sunny day. </fact>
<fact> The cat felt warm. </fact><|im_end|>

```
</details>

---

<a id="phase-2"></a>
### Phase 2: Query Generation

`query-generator-1.5b` deconstructs each atomic fact into three targeted search queries:

```
               Input Atomic Fact:
         "The CEO of Apple is Tim Cook."
                       │
                       ▼
              query-generator-1.5b
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
     ▼                 ▼                 ▼
Pivot Query      Attribute Query   Boolean Query
 (Entity)           (Context)       (Hypothesis)
     │                 │                 │
     ▼                 ▼                 ▼
"Tim Cook"       "CEO of Apple"    "Is Tim Cook the
                                    CEO of Apple?"
```

#### How Generated Queries Are Used Downstream

* **Pivot Query (Entity):** Targets key proper nouns and subjects (e.g., *"Tim Cook"*) to power **BM25 keyword search** (Phase 3).
* **Attribute Query (Context):** Captures underlying properties and relationships (e.g., *"CEO of Apple"*) to drive **dense vector search** via semantic embeddings (Phase 3).
* **Boolean Query (Hypothesis):** Formulates a verifiable statement (e.g., *"Is Tim Cook the CEO of Apple?"*) used by the **cross-encoder** to re-rank chunks (Phase 4).

<details>

<summary>View Sample ChatML</summary>

```xml
<!-- Sample query-generator-1.5b ChatML -->
<|im_start|>system
Generate retrieval queries for the provided atomic fact.<|im_end|>
<|im_start|>user
The CEO of Apple is Tim Cook.<|im_end|>
<|im_start|>assistant
<pivot> Tim Cook </pivot>
<attribute> CEO of Apple </attribute>
<boolean> Is Tim Cook the CEO of Apple? </boolean><|im_end|>
```
</details>

---

<a id="phase-3"></a>
### Phase 3: Dual-Path RAG Retrieval

Retrieves the **Top 30 candidate chunks** per atomic fact by running two parallel search routes and merging them with Reciprocal Rank Fusion (RRF):

| Search Path | Query Used | Algorithm / Model | Strategy |
| --- | --- | --- | --- |
| **Sparse** | Pivot Query (`"Tim Cook"`) | **BM25** (Best Matching 25) | Keyword & entity matching over tokenized text. |
| **Dense** | Attribute Query (`"CEO of Apple"`) | `all-MiniLM-L6-v2` | Embedding vector similarity over chunk semantics. |

* **Fusion:** Merges both candidate lists using **Reciprocal Rank Fusion (RRF)** ($k=60$) to select the **Top 30 overall chunks**.

---

<a id="phase-4"></a>
### Phase 4: Cross-Encoder Re-Ranking

Pairs the **Boolean Query** against the 30 retrieved candidates to select the **Top 3 most relevant chunks**.

1. **Pairing:** Form 30 pairs: `(Boolean Query, Candidate Chunk i)`.
2. **Inference:** Pass pairs through `ms-marco-MiniLM-L6-v2` (Cross-Encoder).
3. **Selection:** Sort pairs by logit score descending and slice **Top 3**.

---

<a id="phase-5"></a>
### Phase 5: Fact Judging

`fact-judge-1.7b` compares the atomic fact with each of the top three retrieved chunks independently and assigns one of three labels: `Supported`, `Contradicted`, or `Not Mentioned`.

---

#### 💡 Edge-Case Detection & Judging Logic:

The judge model (`fact-judge-1.7b`) is specifically fine-tuned to handle tricky real-world evaluation scenarios beyond simple keyword matches:

* **Missing / Partial Data (`Not_Mentioned`):** Explicitly handles cases where the retrieved chunk is silent on the claim, preventing false positives when evidence is absent.
* **Temporal & Numerical Discrepancies:** Flags subtle mismatches in dates, quantities, or titles (e.g., distinguishing award years or specific scientific breakthroughs).
* **Entity Ambiguity & Distractors:** Correctly penalizes chunks that discuss related entities or similar concepts but fail to support the *exact* target assertion.
* **Strict Chain-of-Thought Guardrails:** Generates an internal `<think>` trace before emitting a final `<verdict>` (`Supported`, `Contradiction`, or `Not_Mentioned`) to ensure deterministic classification.

<details>

<summary>View Sample ChatML</summary>

```xml
<!-- Sample fact-judge-1.7b ChatML -->
<|im_start|>system
Evaluate if the retrieved text supports the atomic fact.<|im_end|>
<|im_start|>user
Fact: Albert Einstein received the Nobel Prize for his theory of relativity.
Retrieved Text: In 1921, Albert Einstein was awarded the Nobel Prize in Physics for his services to Theoretical Physics, and especially for his discovery of the law of the photoelectric effect.<|im_end|>
<|im_start|>assistant
<think> The fact claims the prize was for relativity, but text states photoelectric effect. </think>
<verdict> Contradiction </verdict><|im_end|>
```
</details>

---

<a id="phase-6-7"></a>
### Phase 6 & 7: Verification & Decision Logic

```
   Per Atomic Fact (Phase 6)
   ┌────────────────────────────────────────────────────────┐
   │ • ≥ 1 Contradiction        ──►  FAIL                   │
   │ • ≥ 1 Supported (0 Cont)   ──►  SUCCESS                │
   │ • Otherwise                ──►  INSUFFICIENT_DATA      │
   └────────────────────────────────────────────────────────┘
                               │
                               ▼
     Per Sentence (Phase 7)
   ┌────────────────────────────────────────────────────────┐
   │ • Any linked Fact = FAIL   ──►  Sentence FAIL          │
   │ • All linked Facts = PASS  ──►  Sentence PASS          │
   └────────────────────────────────────────────────────────┘


```

* **Audit Trail:** Every evaluation binds the final verdict back to the exact source document with a reason log.

---

<a id="model-zoo"></a>
## 🛠 Model Zoo

All specialized models, weights, and quantized GGUF binaries powering the pipeline stages are sourced from Hugging Face:

| Pipeline Stage | Model Name | Model Type | HF Repository & Direct Link |
| --- | --- | --- | --- |
| **Phase 1: Fact Extraction** | `fact-extractor-1.7b` | `generative` | [🤗 Repository](https://huggingface.co/adrianmm12/fact-extractor-1.7b) · [📥 Direct GGUF Download](https://huggingface.co/adrianmm12/fact-extractor-1.7b/resolve/main/fact-extractor-1.7b-q8_0.gguf) |
| **Phase 2: Query Generation** | `query-generator-1.5b` | `generative` | [🤗 Repository](https://huggingface.co/adrianmm12/Qwen-1.5B-Query-Generator) · [📥 Direct GGUF Download](https://huggingface.co/adrianmm12/Qwen-1.5B-Query-Generator/resolve/main/query-generator-1.5b-Q8_0.gguf) |
| **Phase 3: Dense Retrieval** | `embedder` (`all-MiniLM-L6-v2`) | `embedder` | [🤗 Repository](https://huggingface.co/leliuga/all-MiniLM-L6-v2-GGUF) · [📥 Direct GGUF Download](https://huggingface.co/leliuga/all-MiniLM-L6-v2-GGUF/resolve/main/all-MiniLM-L6-v2.Q4_K_M.gguf) |
| **Phase 4: Re-ranking** | `reranker` (`ms-marco-MiniLM-L6-v2`) | `crossencoder` | [🤗 Repository](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) · [📥 Assets Bundle](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/tree/main) |
| **Phase 5: Fact Judge** | `fact-judge-1.7b` | `generative` | [🤗 Repository](https://huggingface.co/adrianmm12/fact-judge-1.7b) · [📥 Direct GGUF Download](https://huggingface.co/adrianmm12/fact-judge-1.7b/resolve/main/fact-judge-1.7b-q8_0.gguf) |

---
