"""
Manages the dynamic provisioning lifecycle for new enterprises, establishing their logical database isolation.
Provides the secure vaulting endpoints to store third-party API credentials (like Zendesk or Shopify) for the agents.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db_session
from app.database.model import Tenant, TenantCredential, TenantKnowledge
from app.core.security import SecretVault
from app.services.embedding import EmbeddingService

router = APIRouter(prefix="/tenants", tags=["Tenant Management"])

# --- Request/Response Validation Schemas ---

class TenantCreateSchema(BaseModel):
    company_name: str = Field(..., max_length=255, description="Official enterprise identifier name")

class TenantResponseSchema(BaseModel):
    id: str
    company_name: str

    class Config:
        from_attributes = True

class CredentialCreateSchema(BaseModel):
    integration_name: str = Field(..., max_length=100, description="Target provider identifier, e.g., 'openai'")
    plain_text_token: str = Field(..., description="Raw token secret to be encrypted and vaulted")

class KnowledgeCreateSchema(BaseModel):
    document_title: str = Field(..., max_length=255, description="Metadatabase structural title")
    raw_content: str = Field(..., description="Unstructured documentation payload for context generation")


# --- Endpoint Route Definitons ---

@router.post("", response_model=TenantResponseSchema, status_code=status.HTTP_201_CREATED)
async def provision_tenant(payload: TenantCreateSchema, db: AsyncSession = Depends(get_db_session)):
    """
    Onboards a brand new tenant corporate profile into the persistence layer.
    """
    tenant_id = str(uuid.uuid4())
    new_tenant = Tenant(id=tenant_id, company_name=payload.company_name)
    
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    return new_tenant


@router.post("/{tenant_id}/credentials", status_code=status.HTTP_201_CREATED)
async def vault_tenant_credential(
    tenant_id: str, 
    payload: CredentialCreateSchema, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Encrypts a third-party token via AES-256-GCM and pairs it securely to the tenant profile.
    """
    # Verify target tenant profile presence
    tenant_query = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant_query.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Target tenant entity not found")
        
    # Execute hardware-accelerated encryption pipeline
    ciphertext, nonce = SecretVault.encrypt_token(payload.plain_text_token)
    
    new_credential = TenantCredential(
        tenant_id=tenant_id,
        integration_name=payload.integration_name,
        encrypted_token=ciphertext,
        encryption_nonce=nonce
    )
    
    db.add(new_credential)
    await db.commit()
    return {"status": "success", "detail": f"Credential vaulted securely for integration: {payload.integration_name}"}


@router.post("/{tenant_id}/knowledge", status_code=status.HTTP_201_CREATED)
async def ingest_knowledge_document(
    tenant_id: str, 
    payload: KnowledgeCreateSchema, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Transforms plain text records into 1536-dimensional vectors and ingests into HNSW index context.
    """
    # Verify target tenant profile presence
    tenant_query = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant_query.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Target tenant entity not found")

    # Generate isolated vector representation matching target document payload
    embedding_vector = EmbeddingService.generate_embedding(payload.raw_content)

    new_knowledge = TenantKnowledge(
        tenant_id=tenant_id,
        document_title=payload.document_title,
        raw_content=payload.raw_content,
        embedding=embedding_vector
    )

    db.add(new_knowledge)
    await db.commit()
    return {"status": "success", "detail": "Document context processed and injected into database index graph"}