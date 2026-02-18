import uuid
import logging
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, status

from pydantic import BaseModel, Field
from src.graph_orchestrator import GraphOrchestrator

# Standardized logging for request tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusAPI - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NexusOps Agent Gateway",
    version="1.0.0",
    description="Interface for the SRE Agentic RAG Graph."
)

# Persistent orchestrator instance
orchestrator = GraphOrchestrator()
nexus_graph = orchestrator.build_graph()

# --- Schema Definitions ---

class UserQuery(BaseModel):
    text: str = Field(..., min_length=1)
    thread_id: Optional[str] = None

class MessageFrame(BaseModel):
    role: str
    content: Any
    tool_calls: Optional[List] = None

class ChatResponse(BaseModel):
    history: List[MessageFrame]
    thread_id: str

# --- API Implementation ---

@app.post("/v1/chat", response_model=ChatResponse)
async def process_agent_query(query: UserQuery):
    """
    Main entry point for agent interaction. 
    Handles asynchronous graph streaming and state serialization.
    """
    # Maintain state continuity via thread_id
    session_id = query.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    
    execution_history = []
    initial_state = {"messages": [("user", query.text)]}
    
    try:
        # Stream graph values to capture incremental reasoning steps
        async for event in nexus_graph.astream(initial_state, config=config, stream_mode="values"):
            if "messages" not in event:
                continue
                
            msg = event["messages"][-1]
            
            # Map LangChain types to serializable SRE roles
            role_map = {"ai": "assistant", "human": "user", "tool": "system"}
            
            execution_history.append(MessageFrame(
                role=role_map.get(msg.type, msg.type),
                content=msg.content,
                tool_calls=getattr(msg, "tool_calls", None)
            ))

        return ChatResponse(history=execution_history, thread_id=session_id)

    except Exception as e:
        logger.error(f"Graph execution failed for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agentic runtime encountered a critical processing error."
        )

@app.get("/health")
async def liveness_probe():
    return {"status": "ready", "engine": "LangGraph"}
