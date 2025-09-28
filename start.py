#!/usr/bin/env python3
"""
Quick Start Script for UMBC Degree Planner
This script helps set up and launch the application
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("Error: Python 3.8+ is required")
        print(f"Current version: {version.major}.{version.minor}")
        return False
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ['flask', 'neo4j', 'google-generativeai']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"{package} (installed)")
        except ImportError:
            missing.append(package)
            print(f"{package} (missing)")
    
    return missing

def setup_environment():
    """Set up environment file if it doesn't exist"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from template...")
        env_file.write_text(env_example.read_text())
        print("Please edit .env file with your actual configuration values!")
        return False
    elif env_file.exists():
        print("Environment file exists")
        return True
    else:
        print("No environment configuration found")
        return False

def test_connections():
    """Test database and API connections"""
    try:
        from neo4j_client import Neo4jClient
        client = Neo4jClient()
        if client.test_connection():
            print("Neo4j connection successful")
        else:
            print("Neo4j connection failed")
            print("   Make sure Neo4j is running with UMBC dataset loaded")
    except Exception as e:
        print(f"Neo4j connection error: {e}")
    
    try:
        from gemini_client import GeminiClient
        client = GeminiClient()
        if client.test_connection():
            print("Gemini AI connection successful")
        else:
            print("Gemini AI not configured (optional)")
    except Exception as e:
        print(f"Gemini AI error: {e}")

def main():
    print("UMBC Degree Planner - Quick Start")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path('app.py').exists():
        print("Please run this script from the degree_planner directory")
        sys.exit(1)
    
    # Check dependencies
    print("\nChecking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        sys.exit(1)
    
    # Setup environment
    print("\nSetting up environment...")
    env_ready = setup_environment()
    
    # Test connections
    print("\nTesting connections...")
    test_connections()
    
    # Launch application
    print("\nLaunching UMBC Degree Planner...")
    if env_ready:
        print("All checks passed!")
        print("\nThe application will be available at: http://localhost:5000")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 40)
        
        try:
            from app import app
            app.run(debug=True, host='0.0.0.0', port=5000)
        except KeyboardInterrupt:
            print("\nServer stopped")
        except Exception as e:
            print(f"\nError starting server: {e}")
    else:
        print("\nPlease configure your .env file before launching")
        print("1. Copy .env.example to .env")
        print("2. Update Neo4j and Gemini API credentials")
        print("3. Run this script again")

if __name__ == "__main__":
    main()
