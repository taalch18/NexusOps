from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import time
import uuid
from vector_store_wrapper import VectorStoreWrapper

app = FastAPI(title="NexusOps Ingestion Engine")

# Global Vector Store Instance
vector_store: Optional[VectorStoreWrapper] = None

@app.on_event("startup")
async def startup_event():
    global vector_store
    # Initialize with mock mode allowed if keys are missing
    vector_store = VectorStoreWrapper()
    print("Vector Store Initialized")

class DocumentChunk(BaseModel):
    text: str
    metadata: Optional[Dict] = {}

class IngestionResponse(BaseModel):
    status: str
    count: int
    batch_id: str

@app.post("/ingest", response_model=IngestionResponse)
async def ingest_documents(chunks: List[DocumentChunk], background_tasks: BackgroundTasks):
    """
    Asynchronous ingestion endpoint.
    Accepts text chunks, generates embeddings (via wrapper), and upserts to Pinecone.
    """
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector Store not initialized")

    batch_id = str(uuid.uuid4())
    
    # Prepare documents for upsert
    documents = []
    for chunk in chunks:
        doc_id = str(uuid.uuid4())
        documents.append({
            "id": doc_id,
            "text": chunk.text,
            "metadata": {**chunk.metadata, "batch_id": batch_id, "timestamp": time.time()}
        })

    # Execute Upsert
    # In a real heavy-load scenario, we might push to a queue (Celery/Kafka), 
    # but for this phase using FastAPI background tasks or direct async await is acceptable.
    # The prompt asks for "Asynchronous handling". 
    # Since VectorStoreWrapper.upsert is async, we can await it directly or schedule it.
    # To demonstrate "pipeline" behavior, let's await it to report success/failure 
    # but we could also use background_tasks.add_task(vector_store.upsert, documents)
    
    start_time = time.time()
    try:
        count = await vector_store.upsert(documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    
    duration = time.time() - start_time
    print(f"Ingested {count} documents in {duration:.4f}s")

    return IngestionResponse(status="success", count=count, batch_id=batch_id)

@app.get("/health")
async def health_check():
    return {"status": "operational", "mode": "mock" if vector_store.use_mocks else "production"}
