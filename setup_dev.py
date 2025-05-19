#!/usr/bin/env python3
"""
Setup script for development environment.
This script installs pre-commit hooks and development dependencies.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None, check: bool = True) -> None:
    """Run a command and optionally check its return code."""
    result = subprocess.run(cmd, cwd=cwd, check=False)
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        sys.exit(1)
    return result.returncode


def main() -> None:
    """Main setup function."""
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()

    # Install development dependencies
    print("Installing development dependencies...")
    run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=project_root,
    )

    # Install pre-commit hooks
    print("Installing pre-commit hooks...")
    run_command([sys.executable, "-m", "pre_commit", "install"], cwd=project_root)

    # Run pre-commit on all files
    print("Running pre-commit on all files...")
    print("Note: This may fail on first run as it formats and validates all files.")
    print("You may need to run 'pre-commit run --all-files' again after the initial formatting.")
    result = run_command(
        [sys.executable, "-m", "pre_commit", "run", "--all-files"],
        cwd=project_root,
        check=False,
    )

    if result != 0:
        print("\nSome files were formatted or had issues fixed.")
        print("Please run the following command to verify all issues are resolved:")
        print("pre-commit run --all-files")
    else:
        print("\nAll files passed pre-commit checks!")

    print("\nDevelopment environment setup complete!")


if __name__ == "__main__":
    main()
