"""
Defines the strict typed schema (TypedDict/Pydantic) that serves as the shared memory across the agentic workflow.
Maintains the message history, active tenant context, and intermediate reasoning steps during graph execution.
"""

import operator
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    Defines the structural payload passed between nodes during execution transitions.
    Appends new messages to the existing sequence via the operator.add reducer.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tenant_id: str
    active_prompt: str
    classification_intent: str
    token_usage_meta: dict