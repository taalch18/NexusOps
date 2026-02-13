# NexusOps: Autonomous Agentic RAG System

**NexusOps** is an advanced Agentic RAG system built for Infrastructure & Compliance automation. It uses a modular, phase-gated architecture to ingest knowledge, reason about issues, and execute reliable actions via Kubernetes and GitHub integrations.

## 🚀 Key Features
- **Knowledge Foundation**: Asynchronous ingestion pipeline using FastAPI & Pinecone with local embeddings (MiniLM).
- **Agentic Reasoning**: Graph-based orchestrator for resilient state management.
- **Multi-Tool Integration**: Secure Model Context Protocol (MCP) servers for Kubernetes (log fetching) and GitHub (PR drafting).
- **Reliability Layer**: Human-in-the-Loop (HITL) approval via Slack Webhook.

## 🛠️ Architecture
The system follows a 4-phase implementation:
1.  **Knowledge Layer**: `ingestion_engine.py`, `vector_store_wrapper.py`
2.  **Reasoning Layer**: `graph_orchestrator.py`
3.  **Tooling Layer**: `mcp_tools/` (K8s & GitHub Servers)
4.  **Reliability Layer**: `slack_approver.py`, `main.py`

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Pinecone API Key (Free Tier is fine)
- Slack Webhook URL (for approvals)
- GitHub Token (for PRs)

### Installation
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/nexusops.git
    cd nexusops
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file with your API keys:
    ```env
    PINECONE_API_KEY=pc-...
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
    GITHUB_TOKEN=ghp_...
    ```

## 🏃 Usage

### Run the Agent (Interactive)
Execute the main entry point to simulate a troubleshooting session (OOMKill -> Logs -> PR):
```bash
python -m src.main
```
*The system uses a local MiniLM model for embeddings and heuristic logic for orchestration (No OpenAI required).*

### Run Ingestion API
Start the FastAPI server for document ingestion:
```bash
uvicorn src.ingestion_engine:app --reload
```

## 🐳 Deployment
Build and run with Docker:
```bash
docker build -t nexusops .
docker run -p 8000:8000 --env-file .env nexusops
```

## License
MIT
