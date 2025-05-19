"""
Test script to verify personality initialization and usage
"""

import os
import sys

from src.main import run_with_interface


def main():
    """
    Test that personality is correctly loaded and applied
    """
    # Set up paths
    personality_file = os.path.join(
        os.getcwd(), "src", "agents", "Character_Ronan_valet_orchestrator.json"
    )

    # Verify the file exists
    if not os.path.exists(personality_file):
        print(f"ERROR: Personality file not found at {personality_file}")
        return 1

    print(f"Found personality file at: {personality_file}")

    # Run the application with explicit personality file
    print("Starting application with explicit personality file...")
    run_with_interface(personality_file=personality_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
