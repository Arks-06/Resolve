"""
Exposes the primary REST endpoints for consumer interactions, task status polling, and human-in-the-loop state audits.
Interfaces directly with the LangGraph PostgresSaver checkpointer to fetch and resume paused execution graphs.
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from celery.result import AsyncResult
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from app.database.session import get_db_session
from app.database.model import Tenant, TenantPrompt
from app.queue.tasks import execute_agentic_workflow
from app.core.config import settings
from graph.workflow import compile_decision_engine

# Global database connection pool for the checkpointer
sync_db_url = settings.database_url.replace("+asyncpg", "")
checkpointer_pool = ConnectionPool(conninfo=sync_db_url, max_size=5, kwargs={"autocommit": True})

router = APIRouter(prefix="/chat", tags=["Decision Engine Execution"])

class ChatRequestSchema(BaseModel):
    user_query: str

class TaskDispatchResponseSchema(BaseModel):
    task_id: str
    status: str

@router.post("/{tenant_id}", response_model=TaskDispatchResponseSchema, status_code=status.HTTP_202_ACCEPTED)
async def process_agentic_interaction(
    tenant_id: str,
    payload: ChatRequestSchema,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Validates tenant parameters and offloads graph execution to the background Celery worker.
    """
    tenant_query = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant_query.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Target tenant entity not found")
        
    prompt_query = await db.execute(
        select(TenantPrompt)
        .where(TenantPrompt.tenant_id == tenant_id, TenantPrompt.prompt_key == "refund_agent", TenantPrompt.is_active.is_(True))
    )
    active_prompt = prompt_query.scalar_one_or_none()
    prompt_text = active_prompt.prompt_text if active_prompt else "Default system behavior active."
    
    task = execute_agentic_workflow.delay(
        tenant_id=tenant_id, 
        user_query=payload.user_query, 
        active_prompt=prompt_text
    )
    
    return TaskDispatchResponseSchema(
        task_id=task.id,
        status="PROCESSING"
    )

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Retrieves the execution status and final payload of a dispatched background task.
    """
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING' or task_result.state == 'STARTED':
        return {"task_id": task_id, "status": "PROCESSING"}
    elif task_result.state == 'SUCCESS':
        return {"task_id": task_id, "status": "COMPLETED", "result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"task_id": task_id, "status": "FAILED", "error": str(task_result.info)}
    else:
        return {"task_id": task_id, "status": task_result.state}

@router.get("/state/{task_id}")
async def get_graph_state(task_id: str):
    """
    Reads the serialized memory state of a specific graph thread directly from the PostgreSQL checkpointer.
    Utilized by the frontend dashboard to display pending actions awaiting human override.
    """
    run_config = {"configurable": {"thread_id": task_id}}
    
    # Instantiate without the context manager 'with' statement
    checkpointer = PostgresSaver(checkpointer_pool)
    decision_engine = compile_decision_engine(checkpointer=checkpointer)
    state_snapshot = decision_engine.get_state(run_config)
    
    if not state_snapshot:
        raise HTTPException(status_code=404, detail="Execution state not found")
        
    return {
        "task_id": task_id,
        "next_node": state_snapshot.next,
        "values": state_snapshot.values
    }


@router.post("/resume/{task_id}")
async def resume_graph_execution(task_id: str, tenant_id: str):
    """
    Dispatches a specialized resume task to the Celery broker.
    The worker loads the persistent state associated with the task_id and crosses the interrupt boundary.
    """
    task = execute_agentic_workflow.apply_async(
        kwargs={"tenant_id": tenant_id, "user_query": "", "active_prompt": "", "is_resume": True},
        task_id=task_id  # Enforce identical task_id allocation for state thread continuity
    )
    
    return TaskDispatchResponseSchema(
        task_id=task.id,
        status="RESUMING_EXECUTION"
    )