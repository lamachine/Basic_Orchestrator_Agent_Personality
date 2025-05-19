"""
Tests for template_graph.py.

This module tests the template graph implementation, including:
1. Graph creation and compilation
2. Node and edge additions
3. Graph execution
4. Error handling
"""

import asyncio
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, ValidationError

from ...src.common.graphs.template_graph import build_template_graph
from ...src.common.state.state_models import GraphState, MessageRole, MessageStatus


class TestTemplateGraph:
    """Test suite for template graph functionality."""

    def test_build_template_graph_basic(self):
        """Test basic template graph creation."""
        # Test case: Normal operation - should pass
        graph = build_template_graph()

        # Verify the graph was created
        assert graph is not None
        # Verify the graph has a run method
        assert hasattr(graph, "run")

    def test_graph_state_input_validation(self):
        """Test that the graph validates state inputs correctly."""
        # Test case: Error condition - should fail but handle gracefully
        graph = build_template_graph()

        # Create an invalid state (missing required fields)
        invalid_state = {"missing_required_fields": True}

        # Execute with invalid state should raise error
        with pytest.raises(Exception):
            asyncio.run(graph.ainvoke(invalid_state))

    def test_empty_graph_execution(self):
        """Test execution of the empty template graph."""
        # Test case: Edge case - graph with no nodes just returns input state
        graph = build_template_graph()

        # Create a minimal valid state
        minimal_state = GraphState()

        # Execute
        result = asyncio.run(graph.ainvoke(minimal_state))

        # Verify result is the same as input (empty graph)
        assert result == minimal_state


class TestGraphIntegration:
    """Integration tests for template graph with real components."""

    @pytest.mark.asyncio
    async def test_graph_with_mock_node(self):
        """Test graph with a mocked node function."""
        from langgraph.graph import StateGraph

        # Create state model
        class TestState(BaseModel):
            counter: int = 0

        # Create a custom graph for testing
        graph = StateGraph(TestState)

        # Add mock node
        async def increment_counter(state: TestState):
            state.counter += 1
            return state

        graph.add_node("increment", increment_counter)
        graph.set_entry_point("increment")
        graph.set_finish_point("increment")

        # Compile and run
        compiled_graph = graph.compile()

        # Execute graph
        result = await compiled_graph.ainvoke(TestState(counter=0))

        # Verify node executed
        assert result.counter == 1

    @pytest.mark.asyncio
    async def test_graph_with_conditional_edges(self):
        """Test graph with conditional routing between nodes."""
        from langgraph.graph import StateGraph

        # Create state model
        class TestState(BaseModel):
            value: int = 0
            path_taken: str = ""

        # Create a custom graph for testing
        graph = StateGraph(TestState)

        # Add nodes
        async def node_a(state: TestState):
            state.path_taken += "A"
            return state

        async def node_b(state: TestState):
            state.path_taken += "B"
            return state

        # Add conditional router
        def router(state: TestState):
            if state.value > 5:
                return "node_b"
            return "node_a"

        # Build graph
        graph.add_node("node_a", node_a)
        graph.add_node("node_b", node_b)
        graph.set_entry_point("router")
        graph.add_conditional_edges("router", router, {"node_a": "end", "node_b": "end"})

        # Compile graph
        compiled_graph = graph.compile()

        # Test low value (should route to A)
        result_low = await compiled_graph.ainvoke(TestState(value=3))
        assert result_low.path_taken == "A"

        # Test high value (should route to B)
        result_high = await compiled_graph.ainvoke(TestState(value=7))
        assert result_high.path_taken == "B"

    @pytest.mark.asyncio
    async def test_graph_state_persistence(self):
        """Test that graph maintains state between nodes."""
        from langgraph.graph import StateGraph

        # Create state model with multiple fields
        class ComplexState(BaseModel):
            counter: int = 0
            messages: list[str] = []
            metadata: dict = {}

        # Create a custom graph for testing
        graph = StateGraph(ComplexState)

        # Add nodes that update different parts of state
        async def update_counter(state: ComplexState):
            state.counter += 1
            return state

        async def add_message(state: ComplexState):
            state.messages.append(f"Message {state.counter}")
            return state

        async def update_metadata(state: ComplexState):
            state.metadata["last_update"] = "test_time"
            state.metadata["counter"] = state.counter
            return state

        # Build graph with sequential nodes
        graph.add_node("update_counter", update_counter)
        graph.add_node("add_message", add_message)
        graph.add_node("update_metadata", update_metadata)

        graph.set_entry_point("update_counter")
        graph.add_edge("update_counter", "add_message")
        graph.add_edge("add_message", "update_metadata")
        graph.set_finish_point("update_metadata")

        # Compile and run
        compiled_graph = graph.compile()
        initial_state = ComplexState()
        result = await compiled_graph.ainvoke(initial_state)

        # Verify all state updates persisted
        assert result.counter == 1
        assert len(result.messages) == 1
        assert result.messages[0] == "Message 1"
        assert "last_update" in result.metadata
        assert result.metadata["counter"] == 1


# Additional tests specific to our template graph implementation
class TestTemplateGraphSpecifics:
    """Tests for template graph-specific functionality."""

    @pytest.mark.skip("TODO: Implement when template graph is extended")
    def test_parent_request_id_tracking(self):
        """Test parent request ID tracking in metadata."""
        # This will be implemented when the template graph is extended
        pass

    @pytest.mark.skip("TODO: Implement when template graph is extended")
    def test_local_request_id_generation(self):
        """Test local request ID generation and management."""
        # This will be implemented when the template graph is extended
        pass

    @pytest.mark.skip("TODO: Implement when template graph is extended")
    def test_response_preparation(self):
        """Test response preparation for parent graph communication."""
        # This will be implemented when the template graph is extended
        pass

    @pytest.mark.skip("TODO: Implement when template graph is extended")
    def test_subgraph_state_management(self):
        """Test sub-graph specific state management."""
        # This will be implemented when the template graph is extended
        pass
