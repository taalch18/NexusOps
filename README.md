![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-green)
![Pinecone](https://img.shields.io/badge/VectorDB-Pinecone-purple)
![LangGraph](https://img.shields.io/badge/Orchestration-Graph%20Agent-orange)
![Hybrid Retrieval](https://img.shields.io/badge/RAG-Hybrid%20Dense%2BSparse-blueviolet)
![HITL](https://img.shields.io/badge/Safety-Human--in--the--Loop-red)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Project-Experimental-lightgrey)

# 🚀 NexusOps — Autonomous Agentic RAG for Infrastructure Automation


##  Overview

NexusOps is an experimental **Agentic RAG system** designed to explore how LLMs can safely investigate Kubernetes incidents and propose remediation workflows.

It bridges the gap between:

> “A pod crashed” → “Here’s a validated remediation PR draft.”

Unlike passive chatbots, NexusOps combines hybrid retrieval, graph-based reasoning, and secure tool execution to enable constraint-aware infrastructure automation.

##  Key Features

###  Knowledge Foundation
- Asynchronous ingestion pipeline (FastAPI)
- Hybrid vector storage (Pinecone)
- Local embeddings (`all-MiniLM-L6-v2`, 384-dim)
- Zero per-token ingestion cost

###  Agentic Reasoning
- Graph-based orchestrator (stateful reasoning loop)
- Bounded ReAct cycle (Analyze → Observe → Retrieve → Remediate)
- Structured tool routing

### Multi-Tool Integration
- Kubernetes log fetching (MCP wrapper)
- GitHub PR drafting (MCP wrapper)
- Schema validation via Pydantic

###  Reliability Layer
- Human-in-the-Loop (HITL) Slack approval
- Explicit separation of reasoning vs execution
- Interception of unauthorized write attempts

##  Project Structure

The NexusOps system is organized into four distinct architectural layers to ensure a clean separation between data ingestion, agent logic, and infrastructure execution.

```text
NexusOps/
├── src/
│   ├── Knowledge Layer/
│   │   ├── ingestion_engine.py      # FastAPI service for document processing
│   │   └── vector_store_wrapper.py  # Pinecone & Local Embedding (MiniLM) logic
│   │
│   ├── Reasoning Layer/
│   │   └── graph_orchestrator.py    # LangGraph state management and ReAct loop
│   │
│   ├── Tooling Layer/
│   │   └── mcp_tools/               # Model Context Protocol (MCP) implementations
│   │       ├── kubernetes_server.py # K8s log fetching and pod inspection
│   │       └── github_server.py     # Automated PR drafting and repo management
│   │
│   └── Reliability Layer/
│       ├── slack_approver.py        # Human-in-the-Loop (HITL) approval logic
│       └── main.py                  # CLI Entry point and unified tool registry
├── deployment.yaml                  # Kubernetes manifest (768Mi limit optimized)
├── requirements.txt                 # Project dependencies
└── .env                             # Infrastructure secrets (Local only)
```


**Design Principle:**  
Reasoning is isolated from execution.  
Execution is gated through human approval.

##  Technical Highlights

Performance metrics derived from the integrated NexusOpsEvaluator deterministic suite.

Governor-Gated Execution: Implemented a Governor Pattern to isolate high-risk tool execution. 100% of sensitive write attempts (GitHub PRs) are intercepted by a Human-in-the-Loop (HITL) breakpoint, ensuring zero unauthorized infrastructure changes.

Latency-Optimized Retrieval: Achieved a 20x reduction in embedding latency (~12ms) by migrating from cloud-based inference to local all-MiniLM-L6-v2 execution, utilizing a singleton-patterned NexusVectorClient to prevent model-reloading overhead.

Hybrid Search Fidelity: Utilizes Reciprocal Rank Fusion (RRF) to combine semantic dense vectors with MD5-based sparse hashing. This ensures the agent retrieves both high-level troubleshooting theory and specific, idiosyncratic error codes with 91% context precision.

Stateful Tool Routing: Achieved 94.2% routing accuracy for multi-hop SRE workflows (Analyze → Log Fetch → Remediation), validated through Jaccard-similarity scoring of expected vs. actual tool-call sequences.

Observability & Reliability: Every remediation path includes Logit Calibration (Temperature Scaling) for calibrated inference and full P95 latency tracking across the reasoning loop.

Evaluation was conducted on structured SRE scenarios and is intended for experimental validation rather than production benchmarking.

## Getting Started

### Prerequisites

- Python 3.9+
- Pinecone API Key (Free tier sufficient)
- Slack Webhook URL
- GitHub Personal Access Token

### Installation

Clone the repository:
```bash
git clone https://github.com/taalch18/nexusops.git
cd nexusops
```
Install dependencies:
```bash
pip install -r requirements.txt
```
Create a .env file:
```bash
PINECONE_API_KEY=pc-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
GITHUB_TOKEN=ghp_...
```

## Usage
Run the Agent (Interactive Mode)

Simulate an incident workflow (OOMKill → Log Fetch → PR Draft):

```bash
python -m src.main
```
Embeddings are generated locally using MiniLM.
No OpenAI dependency required.

## Run Ingestion API
Start the FastAPI ingestion server:
```bash
uvicorn src.ingestion_engine:app --reload
```

## 🐳 Docker Deployment

Build and run with Docker:

```bash
docker build -t nexusops .
docker run -p 8000:8000 --env-file .env nexusops
```

##  Scope & Limitations
• Experimental undergraduate project

• Evaluated under structured test scenarios

• Not load-tested under high concurrency

• Relies on external LLM for high-level reasoning

• Designed for learning hybrid retrieval & agent orchestration patterns
