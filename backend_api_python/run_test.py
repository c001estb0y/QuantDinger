"""Run futures integration tests"""
import sys
import os

# Set up path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import and run tests
from tests.test_futures_integration import run_integration_tests

if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
