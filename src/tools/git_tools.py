"""
Git Tools for MCP Interface

This module provides Git operations for the MCP interface,
allowing Git commands to be executed through the MCP adapter.
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_git_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Git command through the MCP interface.
    
    Args:
        command: The Git command to execute (e.g., git_status, git_diff)
        params: Parameters for the Git command
        
    Returns:
        Dictionary containing the command result
    """
    try:
        logger.debug(f"Processing Git command: {command}")
        
        # Normalize command by removing git_ prefix if present
        if command.startswith("git_"):
            command = command[4:]
            
        # Get repository path
        repo_path = params.get("repo_path", ".")
        
        # Execute appropriate Git command
        if command == "status":
            return git_status(repo_path)
        elif command == "diff_unstaged":
            return git_diff_unstaged(repo_path)
        elif command == "diff_staged":
            return git_diff_staged(repo_path)
        elif command == "diff":
            target = params.get("target", "HEAD")
            return git_diff(repo_path, target)
        elif command == "commit":
            message = params.get("message", "Commit via MCP")
            return git_commit(repo_path, message)
        elif command == "add":
            files = params.get("files", ["."])
            return git_add(repo_path, files)
        elif command == "reset":
            return git_reset(repo_path)
        elif command == "log":
            max_count = params.get("max_count", 10)
            return git_log(repo_path, max_count)
        elif command == "create_branch":
            branch_name = params.get("branch_name")
            base_branch = params.get("base_branch")
            return git_create_branch(repo_path, branch_name, base_branch)
        elif command == "checkout":
            branch_name = params.get("branch_name")
            return git_checkout(repo_path, branch_name)
        elif command == "show":
            revision = params.get("revision", "HEAD")
            return git_show(repo_path, revision)
        elif command == "init":
            return git_init(repo_path)
        else:
            return {
                "status": "error",
                "error": f"Unsupported Git command: {command}"
            }
    
    except Exception as e:
        error_msg = f"Error processing Git command: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg
        }

def run_git_command(repo_path: str, args: List[str]) -> Dict[str, Any]:
    """
    Run a Git command and return the result.
    
    Args:
        repo_path: Path to the Git repository
        args: Git command arguments
        
    Returns:
        Dictionary containing the command output
    """
    try:
        # Prepare full command with the repository path
        cmd = ["git", "-C", repo_path] + args
        logger.debug(f"Running Git command: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        
        # Check for errors
        if result.returncode != 0:
            return {
                "status": "error",
                "command": " ".join(cmd),
                "error": result.stderr.strip(),
                "code": result.returncode
            }
        
        # Return success
        return {
            "status": "success",
            "command": " ".join(cmd),
            "output": result.stdout.strip(),
            "code": result.returncode
        }
        
    except Exception as e:
        error_msg = f"Error running Git command: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "command": " ".join(["git", "-C", repo_path] + args),
            "error": error_msg
        }

# Git command implementations

def git_status(repo_path: str) -> Dict[str, Any]:
    """Show the working tree status."""
    result = run_git_command(repo_path, ["status"])
    return result

def git_diff_unstaged(repo_path: str) -> Dict[str, Any]:
    """Show changes in the working directory that are not yet staged."""
    result = run_git_command(repo_path, ["diff"])
    return result

def git_diff_staged(repo_path: str) -> Dict[str, Any]:
    """Show changes that are staged for commit."""
    result = run_git_command(repo_path, ["diff", "--staged"])
    return result

def git_diff(repo_path: str, target: str) -> Dict[str, Any]:
    """Show differences between branches or commits."""
    result = run_git_command(repo_path, ["diff", target])
    return result

def git_commit(repo_path: str, message: str) -> Dict[str, Any]:
    """Record changes to the repository."""
    result = run_git_command(repo_path, ["commit", "-m", message])
    return result

def git_add(repo_path: str, files: List[str]) -> Dict[str, Any]:
    """Add file contents to the staging area."""
    result = run_git_command(repo_path, ["add"] + files)
    return result

def git_reset(repo_path: str) -> Dict[str, Any]:
    """Unstage all staged changes."""
    result = run_git_command(repo_path, ["reset"])
    return result

def git_log(repo_path: str, max_count: int = 10) -> Dict[str, Any]:
    """Show commit logs."""
    result = run_git_command(repo_path, ["log", f"-{max_count}", "--oneline"])
    return result

def git_create_branch(repo_path: str, branch_name: str, base_branch: Optional[str] = None) -> Dict[str, Any]:
    """Create a new branch from an optional base branch."""
    if base_branch:
        result = run_git_command(repo_path, ["checkout", "-b", branch_name, base_branch])
    else:
        result = run_git_command(repo_path, ["checkout", "-b", branch_name])
    return result

def git_checkout(repo_path: str, branch_name: str) -> Dict[str, Any]:
    """Switch branches."""
    result = run_git_command(repo_path, ["checkout", branch_name])
    return result

def git_show(repo_path: str, revision: str = "HEAD") -> Dict[str, Any]:
    """Show the contents of a commit."""
    result = run_git_command(repo_path, ["show", revision])
    return result

def git_init(repo_path: str) -> Dict[str, Any]:
    """Initialize a new Git repository."""
    result = run_git_command(repo_path, ["init"])
    return result 