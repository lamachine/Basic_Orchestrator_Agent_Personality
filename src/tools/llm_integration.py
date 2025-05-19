"""LLM integration utilities for tools."""

import json
import re
from typing import Any, Dict, List, Optional

from .initialize_tools import initialize_tools
from .tool_registry import ToolRegistry


class ToolParser:
    """Parse and execute tool calls from LLM responses."""

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """
        Initialize the tool parser.

        Args:
            tool_registry: Optional tool registry to use. If not provided,
                           a new registry will be initialized with default tools.
        """
        self.registry = tool_registry or initialize_tools()

    def extract_tool_calls(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from LLM response text.

        Args:
            llm_response: The text response from the LLM

        Returns:
            List of dictionaries containing tool call information
        """
        # Pattern to match tool calls in format: tool_name(param1="value1", param2="value2")
        # or tool_name(param1='value1', param2='value2')
        # or tool_name(param1=value1, param2=value2) for non-string values
        pattern = r"(\w+)\s*\(\s*(.*?)\s*\)"

        tool_calls = []
        matches = re.finditer(pattern, llm_response)

        for match in matches:
            tool_name = match.group(1)
            params_str = match.group(2)

            # Skip if not a valid tool
            if not self.registry.get_tool(tool_name):
                continue

            # Parse parameters
            params = {}
            if params_str.strip():
                # Replace quotes for consistent parsing
                normalized_params = params_str.replace("'", '"')

                # Try to parse as JSON first
                try:
                    params_dict = f"{{{normalized_params}}}"
                    params = json.loads(params_dict)
                except json.JSONDecodeError:
                    # Fall back to regex parsing
                    param_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]*))'
                    param_matches = re.finditer(param_pattern, params_str)

                    for param_match in param_matches:
                        param_name = param_match.group(1)
                        # Find the non-None value among groups 2, 3, and 4
                        param_value = next(
                            (v for v in param_match.groups()[1:] if v is not None), ""
                        )
                        params[param_name] = param_value

            tool_calls.append({"name": tool_name, "parameters": params})

        return tool_calls

    def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of tool calls.

        Args:
            tool_calls: List of tool call dictionaries as returned by extract_tool_calls

        Returns:
            List of tool execution results
        """
        results = []

        for call in tool_calls:
            result = self.registry.execute_tool(call["name"], **call["parameters"])
            results.append(
                {
                    "name": call["name"],
                    "parameters": call["parameters"],
                    "result": result,
                }
            )

        return results

    def process_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Process an LLM response, extracting and executing any tool calls.

        Args:
            llm_response: The text response from the LLM

        Returns:
            Dictionary containing the original response, extracted tool calls,
            and execution results
        """
        tool_calls = self.extract_tool_calls(llm_response)
        results = self.execute_tool_calls(tool_calls) if tool_calls else []

        return {
            "original_response": llm_response,
            "tool_calls": tool_calls,
            "execution_results": results,
        }

    def format_results_for_llm(self, execution_results: List[Dict[str, Any]]) -> str:
        """
        Format tool execution results for inclusion in the next LLM prompt.

        Args:
            execution_results: List of tool execution results

        Returns:
            Formatted string to include in the next LLM prompt
        """
        if not execution_results:
            return ""

        output = "\n## TOOL EXECUTION RESULTS\n\n"

        for result in execution_results:
            tool_name = result["name"]
            params = result["parameters"]
            params_str = ", ".join(f"{k}='{v}'" for k, v in params.items())

            output += f"### {tool_name}({params_str})\n"
            if isinstance(result["result"], dict):
                # If the result has a message field, use it
                if "message" in result["result"]:
                    output += f"{result['result']['message']}\n\n"
                else:
                    output += f"{json.dumps(result['result'], indent=2)}\n\n"
            else:
                output += f"{str(result['result'])}\n\n"

        return output
