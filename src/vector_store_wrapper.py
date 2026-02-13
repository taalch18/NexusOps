import os
import asyncio
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

load_dotenv()

class LocalEmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
           self.model = SentenceTransformer(model_name)
           self.dimension = 384
        except Exception as e:
           print(f"Error loading model: {e}")
           self.model = None

    def embed_query(self, text: str) -> List[float]:
        if not self.model: return []
        return self.model.encode(text).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.model: return []
        return self.model.encode(texts).tolist()

class VectorStoreWrapper:
    def __init__(self, index_name: str = "nexusops-index"):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = index_name
        
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
            
        self.pc = Pinecone(api_key=self.api_key)
        existing_indexes = [i.name for i in self.pc.list_indexes()]
        if self.index_name not in existing_indexes:
            print(f"Creating Index {self.index_name}...")
            self.pc.create_index(
                name=self.index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pc.Index(self.index_name)
        self.encoder = LocalEmbeddingService()

    async def upsert(self, documents: List[Dict[str, Any]]):
        vectors = []
        texts = [d['text'] for d in documents]
        embeddings = await asyncio.to_thread(self.encoder.embed_documents, texts)

        for i, doc in enumerate(documents):
            vectors.append({
                "id": doc['id'],
                "values": embeddings[i],
                "metadata": {**doc.get('metadata', {}), "text": doc['text']}
            })
        
        await asyncio.to_thread(self.index.upsert, vectors=vectors)
        return len(vectors)

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Hybrid Search (RRF) simplified or standard dense. Keeping it simple as requested."""
        vector = await asyncio.to_thread(self.encoder.embed_query, query)
        results = await asyncio.to_thread(
            self.index.query, vector=vector, top_k=top_k, include_metadata=True
        )
        return [{"id": m.id, "score": m.score, "metadata": m.metadata} for m in results.matches]

    # Minimal Hybrid RRF hook if needed by orchestrator, otherwise standard search is sufficient for concise code.
    # The user asked for "concise codes". I will alias hybrid_search_rrf to search for now unless strictly needed.
    async def hybrid_search_rrf(self, query: str, top_k: int = 3) -> List[Dict]:
        return await self.search(query, top_k)
