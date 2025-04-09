"""
Questions:
1. How does the state in here equate to langgraph's built-in state?
2. Why are we using JSONb to store to the database?  Also, where and how?  
   I see the decode section but not the encode section.
3. When task agents are running synchronously, do they only block their own thread?
4. What is astream in this graph?
Notes:
- results .run is syncronous, .run_stream is asyncronous

Reference:
https://github.com/coleam00/ottomator-agents/blob/main/pydantic-ai-langgraph-parallelization/agent_graph.py
"""



#Imports
import asyncio
import os
import sys

from typing import Annotated, Dict, List, Any
from typing_extensions import TypedDict
from dataclasses import dataclass

# LangX imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

# Pydantic imports
from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

# Import the agents
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .agent_template import agent_template_agent, Agent_Template_Dependencies
from .synthesyzer_agent_template import synthesyzer_agent
from .input_query_template import input_query_agent, Key_Input_Data_Structure 

# Graph State
class GraphState(TypedDict):
        # Chat messages and graph general details
    user_input: str
    # Next line builds the conversation history manually
    # The List format is bytes because we are storing in JSONb
    messages: Annotated[List[bytes], lambda x, y: x + y]
    Key_Info_Data_Structure: Dict[str, Any]

    # User preferences
    general_user_pref: List[str]
    user_graph_prefs: List[str]
    
    # Results from each agent
    agent_template_results: str
    agent_2_results: str
    
    # Final summary
    synthesyzer_agent_results: str

# Node functions for the graph
# These are effectively the containers for the agents defined in the agent files

## input_query_agent functions
async def input_query_agent_node(ctx: StateGraph, state: GraphState, writer) -> Dict[str, Any]:
    """Gather necessary travel information from the user."""
    user_input = state["user_input"]

    # Get the message history into the format for Pydantic AI
    message_history: list[ModelMessage] = []
    for message_row in state['messages']:
        # The ModelMessagesTypeAdapter will convert JSONb to pydantic message python object
        message_history.extend(ModelMessagesTypeAdapter.validate_json(message_row))    


    # Call the info gathering agent
    # Line below lets it display without streaming... much simpler
    # result = await info_gathering_agent.run(user_input)
    #
    # This is the streaming version, the most complex portion of the graph
    async with input_query_agent.run_stream(user_input, message_history=message_history) as result:
        curr_response = ""
        # This is message validation
        # debounce by controls the rate of validation, makes it smoother
        async for message, last in result.stream_structured(debounce_by=0.01):  
            try:
                if last and not Key_Input_Data_Structure.complete:
                    raise Exception("Incorrect user input details returned by the agent.")
                travel_details = await result.validate_structured_result(  
                    message,
                    allow_partial=not last
                )
            except ValidationError as e:
                continue

            if Key_Input_Data_Structure.response:
                writer(Key_Input_Data_Structure.response[len(curr_response):])
                curr_response = Key_Input_Data_Structure.response  

    # Return the response asking for more details if necessary
    # In LangGraph you nodes just return a dictionary with the pieces
    # of the state you want to update
    data = await result.get_data()
    return {
        "agent_template_details": data.model_dump(), 
        "messages": [result.new_messages_json()]
    }

## Agent 1 node
async def agent_template_node(ctx: StateGraph, state: GraphState, writer) -> Dict[str, Any]:
    """Run the first agent."""
    writer("\n#### Getting Agent Template recommendations...\n")
    Key_Input_Data_Structure = state["Key_Input_Data_Structure"]
    user_graph_prefs = state['user_graph_prefs']
    
    # Create Agent 1 dependencies (in a real app, this would come from user preferences)
    agent_template_dependencies = Agent_Template_Dependencies(user_graph_prefs=user_graph_prefs)
    
    # Prepare the prompt for the agent 1 query
    prompt = f"I need Agent Template recommendations from {Key_Input_Data_Structure['data_point_1']} to {Key_Input_Data_Structure['data_point_2']} on {Key_Input_Data_Structure['data_point_3']}. Return  {Key_Input_Data_Structure['data_point_4']}."
    
    # Call the agent and wait for the results
    # This a syncronous call because it is never seen, it just runs and returns reult
    result = await input_query_agent.run(prompt, deps=agent_template_dependencies)
    
    # Return the flight recommendations
    # This is just one entry in the state dictionary
    return {"agent_template_results": result.data}


## Agent 2 node


## Synthesyzer agent node
async def synthesyzer_agent_node(ctx: StateGraph, state: GraphState, writer) -> Dict[str, Any]:
    """Run the synthesyzer agent."""
    agent_template_agent_details = state["agent_template_agent_details"]
    agent_2_results = state["agent_2_results"]

    # Call the final planner agent
    async with synthesyzer_agent.run_stream(prompt) as result:
        # Stream partial text as it arrives
        async for chunk in result.stream_text(delta=True):
            writer(chunk)
    
    # Return the final plan
    data = await result.get_data()
    return {"final_answer": data}

# Conditional edge functions 
def route_after_info_gathering(state: GraphState) -> str:
    """Determine what to do after gathering information."""
    Key_Input_Data_Structure = state["Key_Input_Data_Structure"]
    
    # If all details are not given, we need more information
    if not Key_Input_Data_Structure.get("all_details_given", False):
        return "get_next_user_message"
    
    # If all details are given, we can proceed to parallel agent calls
    # Return a list of Send objects to fan out to multiple nodes
    return ["agent_template_recommendations", "agent_2_recommendations"]


# Human in the look interrupt functions
# Interrupt the graph to get the user's next message
def get_next_user_message(state: GraphState):
    value = interrupt({})

    # Set the user's latest message for the LLM to continue the conversation
    return {
        "user_input": value
    }   


# Build the graph

def build_agent_template_graph():
    """Build and return the agent template graph."""
    # Create the graph with our state
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("input_query_agent_node", input_query_agent_node)
    graph.add_node("get_next_user_message", get_next_user_message)
    graph.add_node("agent_template_node", agent_template_node)
    graph.add_node("agent_2_node", agent_2_node)
    graph.add_node("synthesyzer_agent_node", synthesyzer_agent_node)
    
    # Add edges
    graph.add_edge(START, "input_query_agent_node")
    
    # Conditional edge after info gathering
    graph.add_conditional_edges(
        "input_query_agent_node",
        route_after_info_gathering, # makes the decision, returns nodes
        # The list below is all the possible answers that can be returned
        ["get_next_user_message", "agent_template_node", "agent_2_node"]
    )

    # After getting a user message (required if not enough details given), route back to the info gathering agent
    graph.add_edge("get_next_user_message", "input_query_agent_node")
    
    # Connect all recommendation nodes to the final planning node
    graph.add_edge("agent_template_node", "synthesyzer_agent_node")
    graph.add_edge("agent_2_node", "synthesyzer_agent_node")
    
    # Connect final planning to END
    graph.add_edge("synthesyzer_agent_node", END)
    
    # memory lets it retain data during human in the loop interruptions
    memory = MemorySaver()

    # Compile the graph using checkpointer
    return graph.compile(checkpointer=memory)

# Create the travel agent graph
agent_template_graph = build_agent_template_graph()


# Functions to run the graph locally
# Function to run the travel agent
async def run_agent_template(user_input: str):
    """Run the agent template with the given user input."""
    # Initialize the state with user input
    initial_state = {
        "input_query_template_details": user_input,
        "Key_Input_Data_Structure": {},
        "agent_template_results": [],
        "agent_1_results": [],
        "final_answer": ""
    }
    
    # Run the graph
    result = await agent_template_graph.ainvoke(initial_state)
    
    # Return the final plan
    return result["final_plan"]

async def main():
    # Example user input
    user_input = "I want to plan a trip from New York to Paris from 06-15 to 06-22. My max budget for a hotel is $200 per night."
    
    # Run the travel agent
    final_plan = await run_travel_agent(user_input)
    
    # Print the final plan
    print("Final Answer:")
    print(final_answer)



#  main function
if __name__ == "__main__":
    asyncio.run(main())