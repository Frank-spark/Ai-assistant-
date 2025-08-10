#!/usr/bin/env python3
"""Test runner script for Reflex Executive Assistant."""

import argparse
import subprocess
import sys
import os
from pathlib import Path

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_status(message):
    """Print status message."""
    print(f"{BLUE}[INFO]{NC} {message}")


def print_success(message):
    """Print success message."""
    print(f"{GREEN}[SUCCESS]{NC} {message}")


def print_warning(message):
    """Print warning message."""
    print(f"{YELLOW}[WARNING]{NC} {message}")


def print_error(message):
    """Print error message."""
    print(f"{RED}[ERROR]{NC} {message}")


def run_command(command, description):
    """Run a command and handle errors."""
    print_status(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print_success(f"{description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def run_unit_tests():
    """Run unit tests."""
    command = [
        "python", "-m", "pytest", "tests/unit/",
        "-v", "--tb=short", "--cov=src", "--cov-report=term-missing"
    ]
    return run_command(command, "Unit tests")


def run_integration_tests():
    """Run integration tests."""
    command = [
        "python", "-m", "pytest", "tests/integration/",
        "-v", "--tb=short", "--cov=src", "--cov-report=term-missing"
    ]
    return run_command(command, "Integration tests")


def run_all_tests():
    """Run all tests."""
    command = [
        "python", "-m", "pytest", "tests/",
        "-v", "--tb=short", "--cov=src", "--cov-report=term-missing", "--cov-report=html"
    ]
    return run_command(command, "All tests")


def run_specific_test(test_path):
    """Run a specific test file or test function."""
    command = [
        "python", "-m", "pytest", test_path,
        "-v", "--tb=short"
    ]
    return run_command(command, f"Specific test: {test_path}")


def run_tests_with_marker(marker):
    """Run tests with a specific marker."""
    command = [
        "python", "-m", "pytest", "tests/",
        "-v", "--tb=short", f"-m", marker
    ]
    return run_command(command, f"Tests with marker: {marker}")


def run_tests_parallel():
    """Run tests in parallel."""
    command = [
        "python", "-m", "pytest", "tests/",
        "-v", "--tb=short", "-n", "auto"
    ]
    return run_command(command, "Parallel tests")


def run_tests_with_coverage():
    """Run tests with detailed coverage report."""
    command = [
        "python", "-m", "pytest", "tests/",
        "-v", "--tb=short", "--cov=src", "--cov-report=term-missing", 
        "--cov-report=html", "--cov-report=xml", "--cov-fail-under=80"
    ]
    return run_command(command, "Tests with coverage")


def run_linting():
    """Run code linting."""
    command = ["ruff", "check", "src/", "tests/"]
    return run_command(command, "Code linting")


def run_formatting():
    """Run code formatting."""
    command = ["black", "--check", "src/", "tests/"]
    return run_command(command, "Code formatting check")


def run_formatting_fix():
    """Fix code formatting."""
    command = ["black", "src/", "tests/"]
    return run_command(command, "Code formatting fix")


def run_type_checking():
    """Run type checking."""
    command = ["mypy", "src/"]
    return run_command(command, "Type checking")


def run_security_scan():
    """Run security scanning."""
    command = ["bandit", "-r", "src/"]
    return run_command(command, "Security scanning")


def run_dependency_check():
    """Check for outdated dependencies."""
    command = ["pip", "list", "--outdated"]
    return run_command(command, "Dependency check")


def run_test_cleanup():
    """Clean up test artifacts."""
    cleanup_paths = [
        ".pytest_cache",
        "htmlcov",
        "coverage.xml",
        ".coverage",
        "__pycache__",
        "*.pyc"
    ]
    
    print_status("Cleaning up test artifacts...")
    
    for path in cleanup_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            else:
                os.remove(path)
            print_success(f"Removed: {path}")
    
    print_success("Test cleanup completed")


def show_test_coverage():
    """Show test coverage report."""
    if os.path.exists("htmlcov/index.html"):
        print_status("Opening coverage report in browser...")
        import webbrowser
        webbrowser.open("file://" + os.path.abspath("htmlcov/index.html"))
    else:
        print_warning("Coverage report not found. Run tests with coverage first.")


def run_ci_tests():
    """Run tests as they would be run in CI."""
    commands = [
        (["ruff", "check", "src/", "tests/"], "Linting"),
        (["black", "--check", "src/", "tests/"], "Formatting check"),
        (["mypy", "src/"], "Type checking"),
        (["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--cov=src", "--cov-report=term-missing", "--cov-fail-under=80"], "Tests with coverage")
    ]
    
    all_passed = True
    for command, description in commands:
        if not run_command(command, description):
            all_passed = False
    
    if all_passed:
        print_success("All CI checks passed!")
    else:
        print_error("Some CI checks failed!")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test runner for Reflex Executive Assistant")
    parser.add_argument("command", choices=[
        "unit", "integration", "all", "specific", "marker", "parallel", 
        "coverage", "lint", "format", "format-fix", "types", "security", 
        "deps", "cleanup", "coverage-report", "ci"
    ], help="Test command to execute")
    
    parser.add_argument("--test-path", help="Specific test file or function to run")
    parser.add_argument("--marker", help="Test marker to filter by")
    
    args = parser.parse_args()
    
    # Execute command
    success = False
    
    if args.command == "unit":
        success = run_unit_tests()
    elif args.command == "integration":
        success = run_integration_tests()
    elif args.command == "all":
        success = run_all_tests()
    elif args.command == "specific":
        if not args.test_path:
            print_error("Test path is required for specific test command")
            return 1
        success = run_specific_test(args.test_path)
    elif args.command == "marker":
        if not args.marker:
            print_error("Marker is required for marker command")
            return 1
        success = run_tests_with_marker(args.marker)
    elif args.command == "parallel":
        success = run_tests_parallel()
    elif args.command == "coverage":
        success = run_tests_with_coverage()
    elif args.command == "lint":
        success = run_linting()
    elif args.command == "format":
        success = run_formatting()
    elif args.command == "format-fix":
        success = run_formatting_fix()
    elif args.command == "types":
        success = run_type_checking()
    elif args.command == "security":
        success = run_security_scan()
    elif args.command == "deps":
        success = run_dependency_check()
    elif args.command == "cleanup":
        run_test_cleanup()
        success = True
    elif args.command == "coverage-report":
        show_test_coverage()
        success = True
    elif args.command == "ci":
        run_ci_tests()
        return 0  # CI tests handle their own exit code
    
    if success:
        print_success("Command completed successfully")
        return 0
    else:
        print_error("Command failed")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 