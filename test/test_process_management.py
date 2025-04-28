#!/usr/bin/env python3
"""
Test script for API process management functionality.
This script tests the process tracking and cleanup features.
"""
import requests
import time
import json
import sys

BASE_URL = "http://localhost:5000"

def test_long_task():
    """Test starting and monitoring a long-running task"""
    print("Testing long-running task...")
    
    # 1. Start a long-running task
    response = requests.post(
        f"{BASE_URL}/api/scripts/long-task",
        json={"task_name": "test-cleanup", "duration": 10}
    )
    
    if response.status_code != 200:
        print(f"Error starting long task: {response.text}")
        sys.exit(1)
    
    result = response.json()
    if not result.get("success", False):
        print(f"Error starting long task: {result}")
        sys.exit(1)
    
    process_id = result["process_id"]
    print(f"Started process with ID: {process_id}")
    
    # 2. Check the process status immediately
    response = requests.get(f"{BASE_URL}/api/processes/{process_id}")
    if response.status_code != 200:
        print(f"Error getting process status: {response.text}")
        sys.exit(1)
    
    status = response.json()
    print(f"Initial status: {json.dumps(status, indent=2)}")
    
    # 3. Check all processes
    response = requests.get(f"{BASE_URL}/api/processes")
    if response.status_code != 200:
        print(f"Error listing processes: {response.text}")
        sys.exit(1)
    
    processes = response.json()
    print(f"Found {len(processes['processes'])} tracked processes")
    
    # 4. Wait for the process to complete
    print("Waiting for process to complete...")
    completed = False
    max_checks = 20
    checks = 0
    
    while not completed and checks < max_checks:
        response = requests.get(f"{BASE_URL}/api/processes/{process_id}")
        if response.status_code != 200:
            print(f"Error getting process status: {response.text}")
            break
        
        status = response.json()
        if not status.get("running", True):
            completed = True
            print("Process completed!")
            print(f"Final status: {json.dumps(status, indent=2)}")
        else:
            print(f"Process still running (duration: {status.get('duration', 'unknown')}s)...")
            checks += 1
            time.sleep(1)
    
    if not completed:
        print("Process did not complete in the expected time!")
        sys.exit(1)
    
    # 5. Confirm process is in the completed processes list
    response = requests.get(f"{BASE_URL}/api/processes")
    if response.status_code != 200:
        print(f"Error listing processes: {response.text}")
        sys.exit(1)
    
    processes = response.json()
    process_found = False
    for process in processes["processes"]:
        if process.get("process_id") == process_id:
            process_found = True
            if process.get("running", True):
                print("Error: Process reported as completed but still shows as running!")
                sys.exit(1)
            break
    
    if not process_found:
        print("Error: Completed process not found in process list!")
        sys.exit(1)
    
    print("Test successful: Process was properly tracked and completed!")
    return True

if __name__ == "__main__":
    try:
        if test_long_task():
            print("All tests passed!")
            sys.exit(0)
        else:
            print("Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        sys.exit(1)