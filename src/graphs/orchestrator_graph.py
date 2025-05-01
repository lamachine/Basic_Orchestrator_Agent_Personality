from langgraph.graph import StateGraph
from src.state.state_models import GraphState

def build_orchestrator_graph() -> StateGraph:
    """
    Build and return the orchestrator graph.

    Returns:
        StateGraph: A configured StateGraph for the orchestrator
    """
    graph = StateGraph(GraphState)
    # TODO: Add nodes and edges as needed
    return graph.compile()
