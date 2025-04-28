#!/usr/bin/env python3
"""
Example script that demonstrates an asynchronous long-running task.
This script will run in the background and doesn't return any output.
"""
import json
import sys
import time
import os

def log_message(message):
    """Log a message to a file for demonstration purposes"""
    log_file = os.path.join(os.path.dirname(__file__), "long_task.log")
    with open(log_file, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {message}\n")

def main():
    """Main function that reads input JSON and simulates a long-running task"""
    # Try to read input JSON if provided
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            log_message("Error parsing input JSON")
            sys.exit(1)
    
    # Log the start of the task
    task_name = input_data.get("task_name", "default-task")
    duration = input_data.get("duration", 30)
    log_message(f"Starting long-running task: {task_name} (duration: {duration}s)")
    
    # Simulate work by sleeping
    for i in range(duration):
        if i % 5 == 0:
            log_message(f"Task {task_name} progress: {i}/{duration}")
        time.sleep(1)
    
    # Log completion
    log_message(f"Task {task_name} completed successfully")

if __name__ == "__main__":
    main()
