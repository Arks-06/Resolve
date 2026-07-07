"""
Orchestrates the construction of the LangGraph by binding nodes, setting conditional edges, and defining interrupt boundaries.
Compiles the StateGraph into a runnable artifact injected with the PostgresSaver checkpointer for persistent memory.
"""

from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.nodes import intent_classifier_node, rag_retrieval_node, response_generation_node
from graph.edges import route_by_intent

def compile_decision_engine(checkpointer=None):
    """
    Compiles the deterministic nodes and conditional routing logic into an executable state machine.
    Injects persistent state checking and Human-in-the-Loop boundaries.
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("classifier", intent_classifier_node)
    workflow.add_node("rag_node", rag_retrieval_node)
    workflow.add_node("generation_node", response_generation_node)
    
    workflow.set_entry_point("classifier")
    
    workflow.add_conditional_edges(
        "classifier",
        route_by_intent,
        {
            "rag_node": "rag_node",
            "generation_node": "generation_node"
        }
    )
    
    workflow.add_edge("rag_node", "generation_node")
    workflow.add_edge("generation_node", END)
    
    # interrupt_before enforces a hard execution pause prior to the generation node.
    # State is serialized to the checkpointer and awaits external continuation signals.
    return workflow.compile(
        checkpointer=checkpointer, 
        interrupt_before=["generation_node"]
    )