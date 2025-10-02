#!/usr/bin/env python3
"""
Test runner script for conversation evaluator tests.

This script runs all unit tests for the conversation evaluator,
specifically focusing on the re_calculate behavior.
"""

import sys
import os
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests in the tests directory"""
    
    # Get the directory containing this script
    test_dir = Path(__file__).parent
    
    # Add src to Python path
    src_dir = test_dir.parent / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-x",  # Stop on first failure
    ]
    
    print("Running conversation evaluator tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, cwd=test_dir.parent)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
