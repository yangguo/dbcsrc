#!/usr/bin/env python3
"""
Enhanced Test Runner for DBCSRC Backend
Supports unit tests, API tests, integration tests, and performance tests
"""

import argparse
import subprocess
import sys
import os
import time
from pathlib import Path

def check_dependencies():
    """Check if required testing dependencies are installed."""
    required_packages = ['pytest', 'pytest-cov', 'requests', 'pandas', 'locust']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + ' '.join(missing_packages))
        return False
    
    return True

def run_command(cmd, description=""):
    """Run a command and return success status."""
    if description:
        print(f"\n🔄 {description}")
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr and result.returncode != 0:
            print(f"Error: {result.stderr}")
        
        return result.returncode == 0
    
    except FileNotFoundError:
        print(f"Error: Command not found. Make sure required tools are installed.")
        return False
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def run_unit_tests(coverage=False, verbose=False, html_report=False):
    """Run unit tests using pytest."""
    cmd = ["python", "-m", "pytest", "test_web_crawler.py"]
    
    if coverage:
        cmd.extend(["--cov=web_crawler", "--cov-report=term-missing"])
        if html_report:
            cmd.extend(["--cov-report=html"])
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Running Unit Tests (pytest)")

def run_consolidated_tests(test_type="all"):
    """Run consolidated test suite."""
    cmd = ["python", "consolidated_test_suite.py"]
    
    if test_type != "all":
        cmd.append(f"--{test_type}")
    
    return run_command(cmd, f"Running Consolidated Tests ({test_type})")

def run_performance_tests(users=10, spawn_rate=2, run_time="60s", host="http://localhost:8000"):
    """Run performance tests using Locust."""
    cmd = [
        "locust",
        "-f", "performance_tests.py",
        "--headless",
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", run_time,
        "--host", host
    ]
    
    return run_command(cmd, f"Running Performance Tests ({users} users, {run_time})")

def run_api_tests():
    """Run API tests."""
    cmd = ["python", "test_enhanced_api.py"]
    return run_command(cmd, "Running Enhanced API Tests")

def check_server_health(host="http://localhost:8000"):
    """Check if the server is running."""
    try:
        import requests
        response = requests.get(f"{host}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running at {host}")
            return True
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not available at {host}: {e}")
        return False

def run_quality_checks():
    """Run code quality checks."""
    success = True
    
    # Check if flake8 is available
    try:
        result = run_command(["flake8", "web_crawler.py", "--max-line-length=100"], "Quality Check (flake8)")
        success = success and result
    except:
        print("⚠️ flake8 not available, skipping quality check")
    
    # Check if bandit is available
    try:
        result = run_command(["bandit", "-r", ".", "-f", "json"], "Security Check (bandit)")
        success = success and result
    except:
        print("⚠️ bandit not available, skipping security check")
    
    return success

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Enhanced DBCSRC test runner")
    
    # Test type selection
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--consolidated", action="store_true", help="Run consolidated test suite")
    parser.add_argument("--all", action="store_true", help="Run all test types")
    
    # Test options
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage report")
    parser.add_argument("--verbose", action="store_true", help="Run tests in verbose mode")
    parser.add_argument("--html-report", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--quality", action="store_true", help="Run code quality checks")
    
    # Performance test options
    parser.add_argument("--users", type=int, default=10, help="Number of users for performance tests")
    parser.add_argument("--spawn-rate", type=int, default=2, help="User spawn rate for performance tests")
    parser.add_argument("--run-time", default="60s", help="Duration for performance tests")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host for tests")
    
    # Specific test selection
    parser.add_argument("--specific", help="Run specific test class or method")
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    print("🚀 DBCSRC Enhanced Test Runner")
    print("=" * 50)
    
    success = True
    
    # Determine what tests to run
    if args.all or (not any([args.unit, args.api, args.integration, args.performance, args.consolidated])):
        # Run all tests
        print("\n📋 Running Complete Test Suite")
        
        # Check server for API tests
        server_available = check_server_health(args.host)
        
        # Run unit tests
        success = success and run_unit_tests(args.coverage, args.verbose, args.html_report)
        
        # Run consolidated tests
        success = success and run_consolidated_tests("all")
        
        # Run performance tests if server is available
        if server_available:
            success = success and run_performance_tests(args.users, args.spawn_rate, args.run_time, args.host)
        else:
            print("⚠️ Skipping performance tests (server not available)")
        
        # Run quality checks
        if args.quality:
            success = success and run_quality_checks()
    
    else:
        # Run specific test types
        if args.unit:
            success = success and run_unit_tests(args.coverage, args.verbose, args.html_report)
        
        if args.api:
            if check_server_health(args.host):
                success = success and run_api_tests()
            else:
                print("❌ Cannot run API tests: server not available")
                success = False
        
        if args.integration:
            success = success and run_consolidated_tests("integration")
        
        if args.performance:
            if check_server_health(args.host):
                success = success and run_performance_tests(args.users, args.spawn_rate, args.run_time, args.host)
            else:
                print("❌ Cannot run performance tests: server not available")
                success = False
        
        if args.consolidated:
            success = success and run_consolidated_tests("all")
        
        if args.quality:
            success = success and run_quality_checks()
    
    # Handle specific test selection
    if args.specific:
        cmd = ["python", "-m", "pytest", f"test_web_crawler.py::{args.specific}"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, f"Running Specific Test: {args.specific}")
    
    # Print final summary
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests completed successfully!")
        if args.html_report:
            print("📊 HTML coverage report generated in htmlcov/")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    print("=" * 50)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())