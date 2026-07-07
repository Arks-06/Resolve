"""
Executes the initial startup migrations, ensuring necessary PostgreSQL extensions (like pgvector) are activated.
Bootstraps the foundational schemas required before the application can accept its first tenant.
"""

import asyncio
from sqlalchemy import text
from app.database.session import engine, Base # Ensures declarative models are registered on Base metadata

async def bootstrap_database() -> None:
    """Creates the structural tables and installs vector extension dependencies natively."""
    async with engine.begin() as conn:
        # Enable the pgvector extension within the active PostgreSQL instance
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        # Compile all tables derived from Base metadata definitions
        await conn.run_sync(Base.metadata.create_all)
        
        # Create an HNSW index on the vector field to optimize isolated lookups
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS tenant_knowledge_embedding_hnsw_idx "
            "ON tenant_knowledge USING hnsw (embedding vector_cosine_ops);"
        ))

if __name__ == "__main__":
    asyncio.run(bootstrap_database())