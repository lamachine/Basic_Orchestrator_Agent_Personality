import traceback

try:
    print("Attempting to import...")
    from other_files_future_use.ai_agent_old import LLMQueryAgent

    print("Import successful!")

    print("Attempting to initialize agent...")
    agent = LLMQueryAgent()
    print("Agent initialized successfully!")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

print("Script completed")
