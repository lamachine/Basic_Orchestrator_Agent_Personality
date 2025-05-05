#!/usr/bin/env python3
"""
Tool Integration Test Runner

This script runs tests for the tool integration system, with options to
run specific test groups or all tests.
"""

import argparse
import os
import subprocess
import sys
from typing import List, Optional


# Define test groups based on our implementation checklist
TEST_GROUPS = {
    "discovery": ["tests/test_tool_registry.py"],
    "interface": ["tests/test_personal_assistant_interface.py"],
    "modular": ["tests/test_modular_structure.py"],
    "state": ["tests/test_tool_state_management.py"],
    "task": ["tests/test_personal_assistant_task_list.py"],
    "dynamic": ["tests/test_dynamic_tool_loading.py"],
    "orchestrator": ["tests/test_orchestrator_tools.py", "tests/test_tool_processor.py"],
}

# Add an "all" group that includes all tests
TEST_GROUPS["all"] = [test for group in TEST_GROUPS.values() for test in group]

# Add group for existing tests
TEST_GROUPS["existing"] = ["tests/test_orchestrator_tools.py", "tests/test_tool_processor.py"]

# Add functionally grouped test combinations
TEST_GROUPS["structure"] = TEST_GROUPS["discovery"] + TEST_GROUPS["modular"]
TEST_GROUPS["functionality"] = TEST_GROUPS["interface"] + TEST_GROUPS["task"]
TEST_GROUPS["integration"] = TEST_GROUPS["dynamic"] + TEST_GROUPS["state"]


def run_tests(test_files: List[str], verbose: bool = False, fail_fast: bool = False) -> bool:
    """
    Run pytest on the specified test files.
    
    Args:
        test_files: List of test files to run
        verbose: Whether to use verbose output
        fail_fast: Whether to exit on first failure
        
    Returns:
        True if all tests passed, False otherwise
    """
    # Base pytest command
    cmd = ["pytest"]
    
    # Add options
    if verbose:
        cmd.append("-v")
    if fail_fast:
        cmd.append("-x")
    
    # Add test files
    cmd.extend(test_files)
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode == 0


def list_test_groups():
    """Print available test groups."""
    print("Available test groups:")
    
    # First show individual test groups
    print("\nIndividual test groups:")
    for group in ["discovery", "interface", "modular", "state", "task", "dynamic", "orchestrator"]:
        print(f"  {group}: {len(TEST_GROUPS[group])} test file(s)")
        for test in TEST_GROUPS[group]:
            print(f"    - {test}")
    
    # Then show combined groups
    print("\nCombined test groups:")
    for group in ["structure", "functionality", "integration", "existing", "all"]:
        test_files = TEST_GROUPS[group]
        print(f"  {group}: {len(test_files)} test file(s)")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run tests for tool integration system"
    )
    
    parser.add_argument(
        "group",
        nargs="?",
        choices=list(TEST_GROUPS.keys()),
        default="all",
        help="Test group to run (default: all)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Use verbose output"
    )
    
    parser.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Exit on first failure"
    )
    
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List available test groups and exit"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.list:
        list_test_groups()
        return 0
    
    # Get test files for the specified group
    test_files = TEST_GROUPS[args.group]
    
    # Check if all test files exist
    missing_files = [file for file in test_files if not os.path.exists(file)]
    if missing_files:
        print(f"Error: The following test files do not exist:")
        for file in missing_files:
            print(f"  - {file}")
        return 1
    
    # Print summary of tests to run
    print(f"Running {len(test_files)} test file(s) in group '{args.group}':")
    for file in test_files:
        print(f"  - {file}")
    print()
    
    # Run tests
    success = run_tests(test_files, verbose=args.verbose, fail_fast=args.fail_fast)
    
    if success:
        print("\nAll tests passed!")
        return 0
    else:
        print("\nTest failures detected.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 