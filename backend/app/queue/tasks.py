"""
Encapsulates the core LangGraph compilation and decision-engine execution logic into non-blocking background tasks.
Injects Langfuse OpenTelemetry tracking and handles synchronous database logging for token cost calculations.
"""

import sys
import os

# System path injection must occur at the beginning
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import json
from celery import Task
from langchain_core.messages import HumanMessage
from langfuse.langchain import CallbackHandler
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langfuse import get_client

from app.queue.celery_app import celery_app
from graph.workflow import compile_decision_engine
from app.core.config import settings

# Initialize Langfuse programmatic evaluation handler
langfuse_handler = CallbackHandler()

# Standard synchronous connection pool for the LangGraph PostgresSaver and background logging
sync_db_url = settings.database_url.replace("+asyncpg", "")
pool = ConnectionPool(conninfo=sync_db_url, max_size=10, kwargs={"autocommit": True})

class LangGraphExecutionTask(Task):
    """
    Custom base class to handle DLQ routing upon final failure exhaustion.
    """
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Intercepts final permanent failure and logs state payload to the Dead-Letter Queue synchronously.
        """
        tenant_id = kwargs.get("tenant_id", "unknown")
        payload_str = json.dumps(kwargs)
        error_reason = str(exc)
        
        with pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO dead_letter_queue (tenant_id, task_id, failed_payload, error_reason, timestamp)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (tenant_id, task_id, payload_str, error_reason)
            )
            
        super().on_failure(exc, task_id, args, kwargs, einfo)

@celery_app.task(bind=True, base=LangGraphExecutionTask, max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
def execute_agentic_workflow(self, tenant_id: str, user_query: str, active_prompt: str, is_resume: bool = False, thread_id: str = None):
    """
    Executes or resumes the deterministic state graph asynchronously.
    Injects Langfuse tracing and Postgres state checkpointing.
    """
    current_task_id = self.request.id
    
    active_thread_id = thread_id if thread_id else current_task_id
    
    # Thread ID enforces strictly isolated conversational memory states per transaction
    run_config = {
        "configurable": {"thread_id": active_thread_id}, 
        "callbacks": [langfuse_handler]
    }
    
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    
    decision_engine = compile_decision_engine(checkpointer=checkpointer)
    
    if is_resume:
        # Resumes execution from the paused interrupt boundary
        final_state = decision_engine.invoke(None, config=run_config)
    else:
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "tenant_id": tenant_id,
            "active_prompt": active_prompt
        }
        final_state = decision_engine.invoke(initial_state, config=run_config)
    
    # Flush Langfuse telemetry buffer to external cloud
    get_client().flush()
    
    # Determine if execution halted at the interrupt boundary or reached end
    current_state = decision_engine.get_state(run_config)
    if current_state.next:
        return {"status": "PAUSED_FOR_HUMAN_AUDIT", "pending_node": current_state.next[0]}
        
    final_message = final_state["messages"][-1].content
    usage_data = final_state.get("token_usage_meta", {"input_tokens": 0, "output_tokens": 0})
    
    input_cost = (usage_data["input_tokens"] / 1_000_000) * 0.59
    output_cost = (usage_data["output_tokens"] / 1_000_000) * 0.79
    total_cost = input_cost + output_cost
    
    # Synchronous direct database insertion utilizing the established pool
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO tenant_cost_logs (tenant_id, transaction_ref, model_name, prompt_tokens, completion_tokens, total_cost_usd, timestamp) 
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (tenant_id, active_thread_id, "llama-3.3-70b-versatile", usage_data["input_tokens"], usage_data["output_tokens"], total_cost)
        )
    
    return {
        "status": "COMPLETED",
        "response": final_message,
        "cost_usd": total_cost
    }