import traceback

try:
    print("Attempting to import...")
    from src.agents.ai_agent import LLMQueryAgent
    print("Import successful!")
    
    print("Attempting to initialize agent...")
    agent = LLMQueryAgent()
    print("Agent initialized successfully!")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

print("Script completed") 