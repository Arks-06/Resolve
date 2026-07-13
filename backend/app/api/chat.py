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
from app.queue.celery_app import celery_app
from app.database.session import get_db_session
from app.database.model import Tenant, TenantPrompt
from app.queue.tasks import execute_agentic_workflow, pool
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
    """Checks Celery status, and checks LangGraph memory if paused."""
    # Check standard Celery status
    task_result = celery_app.AsyncResult(task_id)
    
    # check if Celery thinks it's paused
    if task_result.status in ["SUCCESS", "COMPLETED"]:
        inner_result = task_result.result or {}
        
        if inner_result.get("status") == "PAUSED_FOR_HUMAN_AUDIT":
            checkpointer = PostgresSaver(pool)
            checkpointer.setup()
            decision_engine = compile_decision_engine(checkpointer=checkpointer)
            
            # Use the original task_id as the thread_id
            state = decision_engine.get_state({"configurable": {"thread_id": task_id}})
            
            # If state.next is empty, the graph crossed the boundary and finished
            if state and not state.next:
                final_msg = state.values["messages"][-1].content
                return {
                    "status": "COMPLETED", 
                    "result": {
                        "status": "COMPLETED", 
                        "response": final_msg
                    }
                }

    # it's still running, or genuinely paused and untouched, return normal status
    return {"status": task_result.status, "result": task_result.result}


@router.get("/state/{task_id}")
async def get_graph_state(task_id: str):
    """Extracts the exact readable memory dict for the Admin UI."""
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    decision_engine = compile_decision_engine(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": task_id}}
    state = decision_engine.get_state(config)
    
    # Safely extract the readable values dictionary
    if not state or not hasattr(state, "values"):
        return {"state": "No state found in PostgreSQL for this ID."}
        
    # Convert messages to a readable format before sending to frontend
    readable_state = {}
    for key, value in state.values.items():
        if key == "messages":
            readable_state[key] = [{"type": m.type, "content": m.content} for m in value]
        else:
            readable_state[key] = value

    return {"state": readable_state}


@router.post("/resume/{task_id}")
async def resume_graph_execution(task_id: str, tenant_id: str):
    """
    Dispatches a specialized resume task to the Celery broker.
    The worker loads the persistent state associated with the session and crosses the interrupt boundary.
    """
    # Let Celery auto-generate a brand new task id for this second leg of the journey
    task = execute_agentic_workflow.apply_async(
        kwargs={
            "tenant_id": tenant_id, 
            "user_query": "", 
            "thread_id": task_id,  # Pass the original task_id to load the correct LangGraph memory
            "active_prompt": "", 
            "is_resume": True
        }
    )
    
    # Return the newly generated task.id back to the frontend
    return TaskDispatchResponseSchema(
        task_id=task.id,
        status="RESUMING_EXECUTION"
    )