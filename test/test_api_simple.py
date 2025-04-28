#!/usr/bin/env python3
"""
Simple Python script to test the Flask API endpoints.
This script makes requests to each API endpoint and prints the responses.
"""

import requests
import json
from pprint import pprint
import sys

# Base URL for the API server
BASE_URL = "http://localhost:5000"

def print_separator(title):
    """Print a separator with a title"""
    print("\n" + "="*50)
    print(f" {title} ".center(50))
    print("="*50)

def test_endpoint(endpoint, method="GET", data=None, description=""):
    """Test an API endpoint and print the response"""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\nTesting: {description} ({method} {endpoint})")
    print("-" * 40)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        else:  # POST
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Response:")
            try:
                pprint(response.json())
                print("\n✅ Success")
            except json.JSONDecodeError:
                print(f"Error: Response is not valid JSON: {response.text}")
                print("\n❌ Failed")
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            print("\n❌ Failed")
    
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {url}")
        print("\n❌ Failed")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\n❌ Failed")

def check_server_running():
    """Check if the API server is running"""
    try:
        requests.get(BASE_URL, timeout=5)
        return True
    except requests.exceptions.ConnectionError:
        return False

def main():
    """Main function to run tests"""
    print_separator("Flask API Test Script")
    
    # Check if server is running
    if not check_server_running():
        print("\n❌ Error: API server is not running at", BASE_URL)
        print("Please start the server first: python app.py")
        sys.exit(1)
    
    print("\n✅ API server is running at", BASE_URL)
    
    # Test base endpoint
    test_endpoint("/", description="Base Endpoint")
    
    # Test system info endpoint
    test_endpoint("/api/system", description="System Information")
    
    # Test Docker containers endpoint
    test_endpoint("/api/docker", description="Docker Containers")
    
    # Test command execution endpoint
    command_data = {"command": "echo Hello from Python test script!"}
    test_endpoint("/api/execute", method="POST", data=command_data, 
                 description="Command Execution")
    
    # Test script endpoints
    test_endpoint("/api/scripts", description="List Available Scripts")
    
    # Test the system-status synchronous script - Updated to use the new name
    test_endpoint("/api/scripts/example-system-status", method="POST", data={},
                 description="Execute Example System Status Script")
    
    # Test the long-task asynchronous script - Updated to use the new name
    long_task_data = {"task_name": "test-task", "duration": 5}
    test_endpoint("/api/scripts/example-long-task", method="POST", data=long_task_data,
                 description="Execute Example Long Task Script")
    
    print_separator("Test Completed")
    print("\nIf all tests show 'Success', your API server is working correctly.")

if __name__ == "__main__":
    main()