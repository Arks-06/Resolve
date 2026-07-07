"""
Defines the conditional routing logic and transition functions between nodes in the LangGraph execution path.
Evaluates state mutations to determine the next autonomous action or triggers human-in-the-loop pauses.
"""

from graph.state import AgentState

def route_by_intent(state: AgentState) -> str:
    """
    Conditional edge router directing the execution flow based on classification node output.
    """
    intent = state.get("classification_intent", "general_support")
    
    if intent == "rag_retrieval":
        return "rag_node"
    return "generation_node"