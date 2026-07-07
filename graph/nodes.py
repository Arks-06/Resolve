"""
Encapsulates the discrete execution units of the graph, including LLM invocations and tool utilization.
Mutates the global graph state by appending message histories and executing enterprise API calls.
"""

import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from graph.state import AgentState

# Initialize the Groq language model targeting a fast instruction-tuned Llama model
# Temperature is pinned to 0.0 to enforce strict deterministic outputs for enterprise routing
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0.0 
)

def intent_classifier_node(state: AgentState) -> dict:
    """
    Evaluates the user query using the Groq API to determine structural routing intent.
    """
    system_instruction = (
        "You are an intent routing classifier. Analyze the user's message. "
        "If it relates to enterprise policies, refunds, or rules, output exactly: 'rag_retrieval'. "
        "Otherwise, output exactly: 'general_support'."
    )
    
    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=state["messages"][-1].content)
    ]
    
    response = llm.invoke(messages)
    intent = response.content.strip().lower()
    
    # Enforce strict routing fallback
    if intent not in ["rag_retrieval", "general_support"]:
        intent = "general_support"
        
    return {"classification_intent": intent}

def rag_retrieval_node(state: AgentState) -> dict:
    """
    Simulates semantic vector search against the tenant's isolated pgvector knowledge base.
    """
    simulated_context = "System Knowledge: The standard enterprise policy dictates a 30-day resolution window."
    system_msg = SystemMessage(content=f"Context Retrieved: {simulated_context}")
    return {"messages": [system_msg]}

def response_generation_node(state: AgentState) -> dict:
    """
    Generates the final payload directed back to the requesting client using Groq.
    Captures raw token usage metadata directly from the response object.
    """
    prompt = state.get("active_prompt", "You are a helpful support agent.")
    
    system_msg = SystemMessage(content=prompt)
    execution_messages = [system_msg] + list(state["messages"])
    
    response = llm.invoke(execution_messages)
    
    # Extract usage statistics natively provided by the ChatGroq wrapper
    usage = response.response_metadata.get("token_usage", {})
    usage_meta = {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0)
    }
    
    return {
        "messages": [response],
        "token_usage_meta": usage_meta
    }