# Specialty Graph Implementation

This directory is for implementing specialty graphs that extend or override the base template graph functionality.

## Structure

- `template_graph.py`: Example implementation showing how to extend the base template graph
- `custom_nodes.py`: Custom node implementations specific to this specialty
- `custom_edges.py`: Custom edge definitions and logic

## How to Extend the Template Graph

1. Import the base template graph:
```python
from ...common.graphs.template_graph import build_template_graph
```

2. Create your specialty graph by extending the base:
```python
def build_specialty_graph() -> StateGraph:
    # Get base graph
    graph = build_template_graph()

    # Add specialty nodes
    graph.add_node("specialty_node", specialty_node_function)

    # Add specialty edges
    graph.add_edge("specialty_edge", specialty_edge_function)

    return graph.compile()
```

## How to Override Template Graph Components

1. Create your own implementation of specific components:
```python
def custom_node_function(state: GraphState) -> GraphState:
    # Your custom implementation
    return state
```

2. Register your components with the graph:
```python
graph.add_node("node_name", custom_node_function)
```

## Best Practices

1. Always maintain parent request ID tracking
2. Implement proper error handling and state management
3. Document any custom nodes and edges
4. Test graph functionality thoroughly
5. Keep specialty logic separate from common functionality
