# Specialty Override Examples

This directory contains **example code only** showing how to extend and override the base functionality from the common directory. These examples are not meant for production use.

## Purpose

The code in this directory serves as a reference implementation showing:
1. Where to add specialized behavior
2. How to use override points
3. Best practices for extending base classes

## Directory Structure

```
specialty/
├── agents/
│   ├── llm_special.py     # Examples of LLM behavior customization
│   └── template_agent.py  # Examples of orchestration customization
└── README.md             # This file
```

## Important Notes

1. **All Real Functionality Lives in Common**
   - The actual implementation is in `src/common/`
   - Base classes provide all core functionality
   - Base classes include override points for customization

2. **This Code is Example Only**
   - Do not use this code in production
   - These files show patterns to follow
   - Use as reference for your own implementations

3. **Override Points Available**

   In LLM Agent:
   ```python
   async def query_llm_override(self, prompt: str) -> Optional[str]:
       """Override for custom LLM query handling"""
       return None  # Return None to use default

   async def preprocess_prompt(self, prompt: str) -> str:
       """Override to modify prompts before LLM"""
       return prompt

   async def postprocess_response(self, response: str) -> str:
       """Override to modify LLM responses"""
       return response
   ```

   In Orchestrator Agent:
   ```python
   async def route_request_override(self, request: Dict[str, Any], tool_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
       """Override for custom routing logic"""
       return None  # Return None to use default

   async def preprocess_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
       """Override to modify requests before routing"""
       return request

   async def postprocess_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
       """Override to modify responses after routing"""
       return response
   ```

## Usage

1. Identify which base class you want to extend
2. Create your specialized class in a new file
3. Import the appropriate base class
4. Override only the methods you need to customize
5. Use the override points provided

Example:
```python
from ...common.agents.llm_agent import LLMAgent

class MySpecialLLM(LLMAgent):
    async def preprocess_prompt(self, prompt: str) -> str:
        # Add your custom prompt processing here
        return f"Custom context: {prompt}"
```

## Best Practices

1. Only override what you need to change
2. Use the provided override points
3. Call super() if you need base functionality
4. Keep specializations focused and minimal
5. Document why you're overriding behavior 