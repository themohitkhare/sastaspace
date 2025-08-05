#!/usr/bin/env python3
"""
Comprehensive test runner for the backend application.
Provides various options for running different types of tests.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(command, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False

def run_unit_tests():
    """Run unit tests only"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-m", "unit",
        "--tb=short",
        "-v"
    ], "Unit Tests")

def run_integration_tests():
    """Run integration tests only"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-m", "integration",
        "--tb=short",
        "-v"
    ], "Integration Tests")

def run_api_tests():
    """Run API tests only"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-m", "api",
        "--tb=short",
        "-v"
    ], "API Tests")

def run_model_tests():
    """Run model tests only"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-m", "model",
        "--tb=short",
        "-v"
    ], "Model Tests")

def run_view_tests():
    """Run view tests only"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-m", "view",
        "--tb=short",
        "-v"
    ], "View Tests")

def run_ai_tests():
    """Run AI service tests only"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-m", "ai",
        "--tb=short",
        "-v"
    ], "AI Service Tests")

def run_all_tests():
    """Run all tests with coverage"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "--cov=apps",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml",
        "--tb=short",
        "-v"
    ], "All Tests with Coverage")

def run_tests_parallel():
    """Run tests in parallel for faster execution"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-n", "auto",
        "--tb=short",
        "-v"
    ], "Parallel Tests")

def run_slow_tests():
    """Run slow tests only"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "-m", "slow",
        "--tb=short",
        "-v"
    ], "Slow Tests")

def run_code_quality():
    """Run code quality checks"""
    success = True
    
    # Run flake8
    success &= run_command([
        "python", "-m", "flake8", 
        "apps/", 
        "--max-line-length=100",
        "--ignore=E501,W503"
    ], "Code Style Check (flake8)")
    
    # Run black check
    success &= run_command([
        "python", "-m", "black", 
        "--check", 
        "apps/"
    ], "Code Formatting Check (black)")
    
    # Run isort check
    success &= run_command([
        "python", "-m", "isort", 
        "--check-only", 
        "apps/"
    ], "Import Sorting Check (isort)")
    
    return success

def run_security_checks():
    """Run security checks"""
    return run_command([
        "python", "-m", "bandit", 
        "-r", "apps/",
        "-f", "txt"
    ], "Security Check (bandit)")

def run_performance_tests():
    """Run performance benchmarks"""
    return run_command([
        "python", "-m", "pytest", 
        "apps/", 
        "--benchmark-only",
        "--benchmark-skip"
    ], "Performance Benchmarks")

def main():
    parser = argparse.ArgumentParser(description="Backend Test Runner")
    parser.add_argument(
        "--type", 
        choices=[
            "unit", "integration", "api", "model", "view", "ai", 
            "all", "parallel", "slow", "quality", "security", "performance"
        ],
        default="all",
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sastaspace_project.settings')
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    print("🚀 Backend Test Runner")
    print(f"Working directory: {os.getcwd()}")
    print(f"Test type: {args.type}")
    
    success = False
    
    if args.type == "unit":
        success = run_unit_tests()
    elif args.type == "integration":
        success = run_integration_tests()
    elif args.type == "api":
        success = run_api_tests()
    elif args.type == "model":
        success = run_model_tests()
    elif args.type == "view":
        success = run_view_tests()
    elif args.type == "ai":
        success = run_ai_tests()
    elif args.type == "all":
        success = run_all_tests()
    elif args.type == "parallel":
        success = run_tests_parallel()
    elif args.type == "slow":
        success = run_slow_tests()
    elif args.type == "quality":
        success = run_code_quality()
    elif args.type == "security":
        success = run_security_checks()
    elif args.type == "performance":
        success = run_performance_tests()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 