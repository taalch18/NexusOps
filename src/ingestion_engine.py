import time
import uuid
import logging
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from vector_store_wrapper import NexusVectorClient  # Updated to match our humanized client

# Standardized SRE logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusIngest - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global state for the vector client
vector_client: Optional[NexusVectorClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle. 
    Ensures the vector database connection is established before the API goes live.
    """
    global vector_client
    try:
        vector_client = NexusVectorClient()
        await vector_client.connect()
        logger.info("Service operational: NexusVectorClient connected.")
        yield
    except Exception as e:
        logger.critical(f"Service startup failed: {str(e)}")
        raise RuntimeError("Vector Store connection required for startup.")

app = FastAPI(
    title="NexusOps Ingestion API",
    description="High-throughput ingestion engine for SRE playbooks and log context.",
    lifespan=lifespan
)

class DocumentChunk(BaseModel):
    text: str = Field(..., min_length=1, description="The raw text content to be vectorized.")
    metadata: Dict = Field(default_factory=dict, description="Structured tags for filtering.")

class IngestionResponse(BaseModel):
    status: str
    count: int
    batch_id: str
    latency_ms: float

@app.post(
    "/v1/ingest", 
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED
)
async def ingest_playbooks(chunks: List[DocumentChunk]):
    """
    Processes and upserts a batch of documents into the vector store.
    Generates UUIDs and timestamps for each record to ensure auditability.
    """
    if not vector_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Ingestion engine is currently disconnected from the vector store."
        )

    batch_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    
    # Prepare payload with system-level metadata
    payload = []
    for chunk in chunks:
        payload.append({
            "id": str(uuid.uuid4()),
            "text": chunk.text,
            "metadata": {
                **chunk.metadata, 
                "ingest_batch": batch_id, 
                "ingest_ts": time.time()
            }
        })

    try:
        # Utilizing our 'sync_logs' method which already handles thread-offloading
        count = await vector_client.sync_logs(payload)
    except Exception as e:
        logger.error(f"Batch ingestion failed for ID {batch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to commit batch to vector index."
        )
    
    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"Batch {batch_id} complete: {count} docs in {duration_ms:.2f}ms")

    return IngestionResponse(
        status="success", 
        count=count, 
        batch_id=batch_id,
        latency_ms=round(duration_ms, 2)
    )

@app.get("/health", tags=["Observability"])
async def health_check():
    """
    Liveness and Readiness probe for Kubernetes orchestration.
    """
    if vector_client and vector_client.index:
        return {
            "status": "healthy",
            "uptime": "operational",
            "dependencies": {"vector_store": "connected"}
        }
    
    return {
        "status": "degraded",
        "dependencies": {"vector_store": "disconnected"}
    }, status.HTTP_503_SERVICE_UNAVAILABLE
