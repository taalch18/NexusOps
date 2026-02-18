import os
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

# Setup project-specific logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusOps - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class NexusEncoder:
    """
    Handles MiniLM vectorization. 
    Lazy-loads the model only when the first embedding request hits.
    """
    def __init__(self):
        self._model = None

    def _ensure_model(self):
        if not self._model:
            try:
                # 384-d dense vectors for SRE log context
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Successfully loaded SentenceTransformer model.")
            except Exception as e:
                logger.error(f"Failed to initialize NexusEncoder: {str(e)}")
                raise RuntimeError("Critical: Embedding service unavailable.")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        self._ensure_model()
        return self._model.encode(texts).tolist()

class NexusVectorClient:
    def __init__(self, index_name: str = "nexusops-index"):
        self.index_name = index_name
        self.pc = None
        self.index = None
        self.encoder = NexusEncoder()

    async def connect(self):
        """
        Custom init logic to handle Pinecone connection and index validation.
        """
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            logger.critical("PINECONE_API_KEY missing from environment.")
            raise EnvironmentError("Environment not configured for VectorStore.")

        self.pc = Pinecone(api_key=api_key)
        
        # Check existing cloud indices
        try:
            indices = [i.name for i in self.pc.list_indexes()]
            if self.index_name not in indices:
                logger.info(f"Index {self.index_name} not found. Provisioning...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=384,
                    metric="dotproduct",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            logger.error(f"Pinecone connection error: {e}")
            raise

    def _generate_sparse_map(self, text: str) -> Dict[str, Any]:
        """
        Manual term frequency mapping for Hybrid RRF search.
        """
        tokens = text.lower().split()
        unique_tokens = set(tokens)
        
        # Simple frequency-based sparse vector
        return {
            "indices": [abs(hash(t)) % 10000 for t in unique_tokens],
            "values": [float(tokens.count(t)) for t in unique_tokens]
        }

    async def sync_logs(self, log_entries: List[Dict[str, Any]]):
        """
        Batch upserts Kubernetes logs with metadata for diagnostic retrieval.
        """
        start_time = time.perf_counter()
        raw_text = [entry['text'] for entry in log_entries]
        
        # Offload vectorization to avoid blocking the event loop
        dense_vecs = await asyncio.to_thread(self.encoder.get_embeddings, raw_text)

        payload = []
        for i, entry in enumerate(log_entries):
            payload.append({
                "id": entry['id'],
                "values": dense_vecs[i],
                "sparse_values": self._generate_sparse_map(entry['text']),
                "metadata": {**entry.get('metadata', {}), "text": entry['text']}
            })
        
        await asyncio.to_thread(self.index.upsert, vectors=payload)
        
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(f"Synced {len(payload)} logs to Pinecone in {duration:.2f}ms")
        return len(payload)

    async def retrieve_context(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Hybrid retrieval for incident root-cause analysis.
        """
        dense_query = await asyncio.to_thread(self.encoder.get_embeddings, [query])
        sparse_query = self._generate_sparse_map(query)

        try:
            resp = await asyncio.to_thread(
                self.index.query,
                vector=dense_query[0],
                sparse_vector=sparse_query,
                top_k=limit,
                include_metadata=True
            )
            return [{"id": hit.id, "score": hit.score, "data": hit.metadata} for hit in resp.matches]
        except Exception as e:
            logger.error(f"Search query failed: {e}")
            return []
