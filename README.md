![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-green)
![Pinecone](https://img.shields.io/badge/VectorDB-Pinecone-purple)
![LangGraph](https://img.shields.io/badge/Orchestration-Graph%20Agent-orange)
![Hybrid Retrieval](https://img.shields.io/badge/RAG-Hybrid%20Dense%2BSparse-blueviolet)
![HITL](https://img.shields.io/badge/Safety-Human--in--the--Loop-red)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Project-Experimental-lightgrey)

# NexusOps — Autonomous Agentic RAG for Infrastructure Automation

## Overview

NexusOps is an experimental agentic RAG system that investigates Kubernetes incidents and proposes remediation workflows autonomously, with human approval only at the final destructive step.

It bridges the gap between:

> "A pod crashed" → "Here's a validated remediation PR draft."

Unlike passive chatbots, NexusOps combines hybrid retrieval, LangGraph-based stateful reasoning, and a Governor Pattern safety layer to enable constraint-aware infrastructure automation at zero cloud inference cost.

---

## Key Features

### Knowledge Foundation
- Asynchronous ingestion pipeline (FastAPI)
- Hybrid vector storage (Pinecone serverless)
- Local embeddings (`all-MiniLM-L6-v2`, 384-dim)
- Zero per-token ingestion cost via local Ollama inference

### Agentic Reasoning
- LangGraph StateGraph orchestrator with explicit state machine
- Bounded ReAct cycle (Analyze → Observe → Retrieve → Remediate)
- MAX_ITERATIONS=5 circuit breaker to prevent infinite reasoning loops
- Conditional edge routing separating diagnostic tools from execution tools

### Multi-Tool Integration
- Kubernetes log fetching (MCP wrapper)
- GitHub PR drafting (MCP wrapper)
- Playbook search via RAG retrieval
- Schema validation via Pydantic

### Reliability Layer
- Governor Pattern: `interrupt_before=['governor_gate']` guarantees 100% write interception
- Human-in-the-Loop Slack approval before any infrastructure change
- MemorySaver checkpointing — full AgentState serialized across interrupt boundaries
- Explicit separation of diagnostic tools (read-only) from execution tools (write)

---

## Performance

All metrics from the integrated NexusOpsEvaluator deterministic suite.

| Metric | Value | Method |
|---|---|---|
| Retrieval latency (warm) | ~12ms | `time.perf_counter()` singleton benchmark |
| Latency improvement over cold baseline | 20x | Cold (~240ms) vs warm (~12ms) load comparison |
| RAGAS Faithfulness | 0.95 | RAGAS eval on synthetic SRE playbook dataset |
| Context Precision@3 | ~91% | Binary hit-rate over 10 golden queries |
| Routing accuracy | 94.2% | Jaccard similarity of expected vs actual tool-call sets |
| Unauthorized write interception | 100% | Structural guarantee via LangGraph `interrupt_before` |

> Evaluation conducted on structured synthetic SRE scenarios. Not production-benchmarked.

---

## Project Structure

```text
NexusOps/
├── src/
│   ├── Knowledge Layer/
│   │   ├── ingestion_engine.py      # FastAPI async ingestion service
│   │   └── vector_store_wrapper.py  # Pinecone hybrid retrieval + RRF fusion
│   │
│   ├── Reasoning Layer/
│   │   └── graph_orchestrator.py    # LangGraph StateGraph + ReAct loop
│   │
│   ├── Tooling Layer/
│   │   └── mcp_tools/
│   │       ├── kubernetes_server.py # K8s log fetching
│   │       └── github_server.py     # PR drafting via GitHub API
│   │
│   └── Reliability Layer/
│       ├── slack_approver.py        # HITL Slack webhook + approval gate
│       └── main.py                  # CLI entry point
├── deployment.yaml
├── requirements.txt
└── .env
```

**Design principle:** Reasoning is isolated from execution. Execution is gated through human approval at the framework level, not application logic.

---

## Architecture

```
User Query
    |
    v
FastAPI / CLI Entry
    |
    v
LangGraph StateGraph
    |
    +-- agent_brain() [LLM: Groq LLaMA-3.1-8B, t=0]
    |       |
    |       v
    |   route_decision() [conditional edges]
    |       |
    |       +-- safe_zone --> ToolNode [fetch_k8s_logs, search_playbooks]
    |       |                     |
    |       |                     v
    |       |               loop back to agent_brain()
    |       |
    |       +-- governor_gate --> interrupt_before fires
    |                                 |
    |                                 v
    |                           MemorySaver serializes state
    |                                 |
    |                                 v
    |                           Slack notification to SRE
    |                                 |
    |                                 v
    |                           Human: 'confirm' or 'abort'
    |                                 |
    |                                 v
    |                           graph.invoke(None, config) resumes
    |                                 |
    |                                 v
    |                           create_github_pr() executes
    |
    v
PR URL returned
```

---

## Design Tradeoffs

These are the explicit engineering decisions made during development and why each was chosen over its alternative.

### LangGraph over LangChain AgentExecutor
LangChain's AgentExecutor runs a linear loop with no interrupt support. The HITL Governor Pattern requires the graph to pause mid-execution, serialize full state, and resume after human input. This is only possible with LangGraph's `interrupt_before` hook. AgentExecutor cannot do this without reimplementing the entire execution model from scratch.

**Cost of this choice:** LangGraph has a steeper learning curve and requires explicit node registration, edge declaration, and TypedDict state schemas. The verbosity is justified by the control it provides.

### RRF over Pinecone's native alpha blending
Pinecone's built-in hybrid search uses a weighted alpha parameter to blend dense and sparse scores. This breaks for two reasons: dense scores (cosine similarity, range -1 to 1) and sparse scores (term frequency dot product, range 0 to hundreds) are on incompatible scales, making direct addition mathematically unsound. Alpha also requires per-domain calibration — a value tuned on prose runbooks performs differently on YAML configs or Java stack traces.

RRF fuses by rank position, not raw score. `score(d) = 1/(60 + rank)`. The k=60 constant is universal across domains (Cormack et al., SIGIR 2009) and requires no calibration.

**Cost of this choice:** Two separate Pinecone queries (dense + sparse) instead of one blended query. Mitigated by `asyncio.gather()` running them concurrently.

### MiniLM-L6-v2 over OpenAI text-embedding-3-small
Local model, zero per-query cost, ~80MB on disk, 384-dim vectors fit Pinecone's free tier. The 20x latency improvement claim is specifically about eliminating the singleton reload cost — cold load is ~250ms, warm encode is ~12ms.

**Cost of this choice:** 384-dim vs 1536-dim embeddings. Lower dimensional vectors have slightly reduced retrieval quality on edge cases. Acceptable for demo-scale SRE runbooks where the vocabulary is constrained.

### Groq LLaMA-3.1-8B over GPT-4o or Claude
Free tier, ~500 tok/s inference. Temperature=0 is critical for deterministic tool routing — all candidates support this. GPT-4o quality is higher but costs $5/1M input tokens, unacceptable for a zero-budget project.

**Cost of this choice:** Smaller model with less reasoning depth on complex multi-hop incidents. Mitigated by strong RAG grounding reducing reliance on parametric knowledge.

### MemorySaver over SqliteSaver
Zero infrastructure dependency. In-process only. Suitable for demo.

**Cost of this choice:** Process restart loses all in-flight approvals. Not acceptable in production.

---

## What I'd Do Differently

These are genuine gaps identified during and after development, not afterthoughts.

**1. Real Kubernetes client instead of simulated adapter**
`fetch_k8s_logs()` uses a hardcoded Python dict. A real implementation would use the `kubernetes` Python client with in-cluster RBAC credentials calling `/api/v1/namespaces/{ns}/pods/{pod}/log`. This was skipped due to the complexity of setting up a local K8s cluster for testing. It is the single biggest gap between this project and a production system.

**2. Cross-encoder reranking after RRF**
RRF improves retrieval over single-modality search but still returns chunks that are topically related rather than precisely relevant. Adding a cross-encoder reranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) as a second-stage filter over the top-10 RRF results before passing to the LLM would measurably improve faithfulness. The latency cost is roughly 20-40ms per query — acceptable.

**3. Interactive Slack approval instead of CLI input()**
`await_validation()` blocks the process with `input()`. This prevents handling multiple concurrent incidents and requires CLI access for approval. A production system needs Slack's Interactive Components API — the Slack message contains Approve/Deny buttons, clicking fires an HTTP POST to a FastAPI webhook, which calls `graph.invoke(None, config)` to resume the frozen state.

**4. Durable checkpointing with SqliteSaver**
MemorySaver is lost on process restart. Every in-flight approval waiting for human input would be lost if the server restarts during the pause window. SqliteSaver writes checkpoint state to disk, surviving restarts. This is a one-line change in graph compilation and should have been the default from the start.

**5. Real evaluation dataset**
The 10 synthetic SRE playbooks were generated for this project. Precision and routing accuracy metrics are measured in a controlled environment where the correct answers are known. Real-world validation requires ingesting actual production runbooks and measuring against real incident resolutions.

---

## Getting Started

### Prerequisites
- Python 3.9+
- Pinecone API key (free tier sufficient)
- Groq API key (free)
- Slack webhook URL
- GitHub personal access token

### Installation

```bash
git clone https://github.com/taalch18/nexusops.git
cd nexusops
pip install -r requirements.txt
```

Create `.env`:
```bash
PINECONE_API_KEY=pc-...
GROQ_API_KEY=gsk_...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
GITHUB_TOKEN=ghp_...
```

### Run

```bash
python -m src.main
```

### Run Ingestion API

```bash
uvicorn src.ingestion_engine:app --reload
```

### Docker

```bash
docker build -t nexusops .
docker run -p 8000:8000 --env-file .env nexusops
```

---

## Scope and Limitations

- Experimental undergraduate project, not production-validated
- K8s adapter is simulated — not connected to a real cluster
- Evaluated on synthetic scenarios, not real incident data
- MemorySaver is not durable across process restarts
- Single-threaded approval loop blocks concurrent incident handling
- No CI/CD, no test coverage, no OpenTelemetry tracing

---

*MIT License · github.com/taalch18/NexusOps · Taal Chawla, MAIT GGSIPU Delhi, 2026*
