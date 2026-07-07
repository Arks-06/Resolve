"""
Handles the CRUD operations for registering and versioning tenant-specific system prompt playbooks.
Ensures the correct, active LLM instructions are injected into the agent's memory prior to execution.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.database.session import get_db_session
from app.database.model import Tenant, TenantPrompt

router = APIRouter(prefix="/prompts", tags=["System Prompt Playbooks"])

class PromptCreateSchema(BaseModel):
    prompt_key: str = Field(..., max_length=100, description="Dynamic key tag for system context lookup mapping")
    prompt_text: str = Field(..., description="Complete system framework template instruction context")

class PromptResponseSchema(BaseModel):
    prompt_key: str
    version: int
    prompt_text: str
    is_active: bool

    class Config:
        from_attributes = True

@router.post("/{tenant_id}", response_model=PromptResponseSchema, status_code=status.HTTP_201_CREATED)
async def register_new_prompt_version(
    tenant_id: str,
    payload: PromptCreateSchema,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Registers a new prompt version for a specific tenant, automatically archiving older versions.
    """
    tenant_query = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant_query.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Target tenant entity not found")
        
    version_query = await db.execute(
        select(func.coalesce(func.max(TenantPrompt.version), 0))
        .where(TenantPrompt.tenant_id == tenant_id, TenantPrompt.prompt_key == payload.prompt_key)
    )
    next_version = version_query.scalar_one() + 1
    
    await db.execute(
        update(TenantPrompt)
        .where(TenantPrompt.tenant_id == tenant_id, TenantPrompt.prompt_key == payload.prompt_key)
        .values(is_active=False)
    )
    
    new_prompt = TenantPrompt(
        tenant_id=tenant_id,
        prompt_key=payload.prompt_key,
        version=next_version,
        prompt_text=payload.prompt_text,
        is_active=True
    )
    
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)
    return new_prompt