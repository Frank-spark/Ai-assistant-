#!/usr/bin/env python3
"""Integration Test Runner for Reflex Executive Assistant."""

import argparse
import asyncio
import subprocess
import sys
import time
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


def run_command(command, description, capture_output=True):
    """Run a command and handle errors."""
    print_status(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    
    try:
        if capture_output:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print_success(f"{description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            result = subprocess.run(command, check=True)
            print_success(f"{description} completed successfully")
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


def run_end_to_end_tests():
    """Run end-to-end tests."""
    command = [
        "python", "-m", "pytest", "tests/integration/test_end_to_end.py",
        "-v", "--tb=short", "--cov=src", "--cov-report=term-missing"
    ]
    return run_command(command, "End-to-end tests")


def run_webhook_tests():
    """Run webhook-specific tests."""
    command = [
        "python", "-m", "pytest", "tests/integration/test_webhooks.py",
        "-v", "--tb=short"
    ]
    return run_command(command, "Webhook tests")


def run_database_tests():
    """Run database-related tests."""
    command = [
        "python", "-m", "pytest", "tests/unit/test_models.py",
        "-v", "--tb=short"
    ]
    return run_command(command, "Database model tests")


def run_knowledge_base_tests():
    """Run knowledge base tests."""
    command = [
        "python", "-m", "pytest", "tests/integration/test_end_to_end.py::TestKnowledgeBaseIntegration",
        "-v", "--tb=short"
    ]
    return run_command(command, "Knowledge base integration tests")


def run_performance_tests():
    """Run performance and scalability tests."""
    command = [
        "python", "-m", "pytest", "tests/integration/test_end_to_end.py::TestPerformanceAndScalability",
        "-v", "--tb=short"
    ]
    return run_command(command, "Performance and scalability tests")


def run_health_checks():
    """Run system health checks."""
    command = [
        "python", "-m", "pytest", "tests/integration/test_end_to_end.py::TestSystemHealth",
        "-v", "--tb=short"
    ]
    return run_command(command, "System health checks")


def run_error_handling_tests():
    """Run error handling tests."""
    command = [
        "python", "-m", "pytest", "tests/integration/test_end_to_end.py::TestErrorHandling",
        "-v", "--tb=short"
    ]
    return run_command(command, "Error handling tests")


def run_configuration_tests():
    """Run configuration validation tests."""
    command = [
        "python", "-m", "pytest", "tests/unit/test_config.py",
        "-v", "--tb=short"
    ]
    return run_command(command, "Configuration validation tests")


def run_linting():
    """Run code linting."""
    command = ["ruff", "check", "src/", "tests/"]
    return run_command(command, "Code linting")


def run_formatting_check():
    """Run code formatting check."""
    command = ["black", "--check", "src/", "tests/"]
    return run_command(command, "Code formatting check")


def run_type_checking():
    """Run type checking."""
    command = ["mypy", "src/"]
    return run_command(command, "Type checking")


def run_security_scan():
    """Run security scanning."""
    command = ["bandit", "-r", "src/"]
    return run_command(command, "Security scanning")


def run_coverage_report():
    """Run tests with detailed coverage report."""
    command = [
        "python", "-m", "pytest", "tests/",
        "-v", "--tb=short", "--cov=src", "--cov-report=term-missing", 
        "--cov-report=html", "--cov-report=xml", "--cov-fail-under=80"
    ]
    return run_command(command, "Coverage report")


def run_all_integration_tests():
    """Run all integration tests in sequence."""
    print_status("Starting comprehensive integration test suite...")
    
    test_suites = [
        ("Configuration Validation", run_configuration_tests),
        ("Code Quality", run_linting),
        ("Code Formatting", run_formatting_check),
        ("Type Checking", run_type_checking),
        ("Security Scan", run_security_scan),
        ("Database Models", run_database_tests),
        ("Webhook Integration", run_webhook_tests),
        ("Knowledge Base Integration", run_knowledge_base_tests),
        ("Error Handling", run_error_handling_tests),
        ("System Health", run_health_checks),
        ("Performance Tests", run_performance_tests),
        ("End-to-End Workflows", run_end_to_end_tests),
        ("Coverage Report", run_coverage_report)
    ]
    
    results = {}
    all_passed = True
    
    for test_name, test_function in test_suites:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        success = test_function()
        end_time = time.time()
        
        duration = end_time - start_time
        results[test_name] = {
            "success": success,
            "duration": duration
        }
        
        if success:
            print_success(f"{test_name} passed in {duration:.2f}s")
        else:
            print_error(f"{test_name} failed in {duration:.2f}s")
            all_passed = False
    
    # Print summary
    print(f"\n{'='*60}")
    print("INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    
    total_duration = sum(result["duration"] for result in results.values())
    passed_count = sum(1 for result in results.values() if result["success"])
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result["success"] else "FAIL"
        duration = f"{result['duration']:.2f}s"
        print(f"{test_name:<30} | {status:>4} | {duration:>8}")
    
    print(f"{'='*60}")
    print(f"Total Tests: {total_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {total_count - passed_count}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Overall Status: {'PASS' if all_passed else 'FAIL'}")
    print(f"{'='*60}")
    
    return all_passed


def run_specific_workflow(workflow_type):
    """Run tests for a specific workflow type."""
    workflow_tests = {
        "slack": run_webhook_tests,
        "email": run_webhook_tests,
        "asana": run_webhook_tests,
        "knowledge-base": run_knowledge_base_tests,
        "database": run_database_tests,
        "performance": run_performance_tests,
        "health": run_health_checks,
        "error-handling": run_error_handling_tests,
        "configuration": run_configuration_tests
    }
    
    if workflow_type not in workflow_tests:
        print_error(f"Unknown workflow type: {workflow_type}")
        print(f"Available workflows: {', '.join(workflow_tests.keys())}")
        return False
    
    return workflow_tests[workflow_type]()


def run_continuous_integration():
    """Run tests as they would be run in CI."""
    print_status("Running continuous integration tests...")
    
    ci_tests = [
        ("Configuration Validation", run_configuration_tests),
        ("Code Quality", run_linting),
        ("Code Formatting", run_formatting_check),
        ("Type Checking", run_type_checking),
        ("Security Scan", run_security_scan),
        ("Unit Tests", run_unit_tests),
        ("Integration Tests", run_integration_tests),
        ("Coverage Report", run_coverage_report)
    ]
    
    all_passed = True
    for test_name, test_function in ci_tests:
        print(f"\nRunning: {test_name}")
        if not test_function():
            all_passed = False
            print_error(f"{test_name} failed")
        else:
            print_success(f"{test_name} passed")
    
    if all_passed:
        print_success("All CI tests passed!")
    else:
        print_error("Some CI tests failed!")
    
    return all_passed


def run_load_testing():
    """Run load testing scenarios."""
    print_status("Running load testing scenarios...")
    
    # This would typically involve more sophisticated load testing
    # For now, we'll run the performance tests
    return run_performance_tests()


def run_stress_testing():
    """Run stress testing scenarios."""
    print_status("Running stress testing scenarios...")
    
    # This would typically involve more sophisticated stress testing
    # For now, we'll run the performance tests with higher concurrency
    command = [
        "python", "-m", "pytest", "tests/integration/test_end_to_end.py::TestPerformanceAndScalability",
        "-v", "--tb=short", "-n", "auto"
    ]
    return run_command(command, "Stress testing")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Integration Test Runner for Reflex Executive Assistant")
    parser.add_argument("command", choices=[
        "unit", "integration", "e2e", "webhook", "database", "kb", "performance", 
        "health", "error-handling", "config", "lint", "format", "types", "security",
        "coverage", "all", "ci", "load", "stress", "workflow"
    ], help="Integration test command to execute")
    
    parser.add_argument("--workflow-type", choices=[
        "slack", "email", "asana", "knowledge-base", "database", "performance", 
        "health", "error-handling", "configuration"
    ], help="Specific workflow type to test")
    
    args = parser.parse_args()
    
    # Execute command
    success = False
    
    if args.command == "unit":
        success = run_unit_tests()
    elif args.command == "integration":
        success = run_integration_tests()
    elif args.command == "e2e":
        success = run_end_to_end_tests()
    elif args.command == "webhook":
        success = run_webhook_tests()
    elif args.command == "database":
        success = run_database_tests()
    elif args.command == "kb":
        success = run_knowledge_base_tests()
    elif args.command == "performance":
        success = run_performance_tests()
    elif args.command == "health":
        success = run_health_checks()
    elif args.command == "error-handling":
        success = run_error_handling_tests()
    elif args.command == "config":
        success = run_configuration_tests()
    elif args.command == "lint":
        success = run_linting()
    elif args.command == "format":
        success = run_formatting_check()
    elif args.command == "types":
        success = run_type_checking()
    elif args.command == "security":
        success = run_security_scan()
    elif args.command == "coverage":
        success = run_coverage_report()
    elif args.command == "all":
        success = run_all_integration_tests()
    elif args.command == "ci":
        success = run_continuous_integration()
    elif args.command == "load":
        success = run_load_testing()
    elif args.command == "stress":
        success = run_stress_testing()
    elif args.command == "workflow":
        if not args.workflow_type:
            print_error("Workflow type is required for workflow command")
            return 1
        success = run_specific_workflow(args.workflow_type)
    
    if success:
        print_success("Integration tests completed successfully!")
        return 0
    else:
        print_error("Integration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 