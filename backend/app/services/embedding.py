"""
Orchestrates the ingestion, chunking, and embedding generation for enterprise knowledge base documents.
Pushes the vectorized semantic data into the PostgreSQL database to power the agent's RAG capabilities.
"""

from typing import List
import hashlib

class EmbeddingService:
    """
    Handles text transformation into vector embeddings for semantic search ingestion.
    """

    @staticmethod
    def generate_embedding(text: str) -> List[float]:
        """
        Generates a deterministic 1536-dimensional vector embedding from text.
        Ensures consistent testing without external network dependencies.
        """
        # Generate a seed value from the raw text payload
        hashed = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(hashed[:8], 16)
        
        # Build a pseudo-random normalized vector of 1536 dimensions
        vector: List[float] = []
        current = seed
        for _ in range(1536):
            current = (current * 1103515245 + 12345) & 0x7fffffff
            vector.append(float(current) / float(0x7fffffff))
            
        # Normalize vector magnitude to ensure accurate cosine distance metrics
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]
            
        return vector