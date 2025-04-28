#!/usr/bin/env python3
"""
Docker Manager Script for system dashboard.
This script provides advanced Docker container management capabilities.
"""
import json
import sys
import subprocess
import os
import time

def run_command(cmd):
    """Execute a shell command and return its output."""
    try:
        process = subprocess.run(
            cmd, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return {
            "success": True,
            "returncode": process.returncode,
            "stdout": process.stdout.strip(),
            "stderr": process.stderr.strip()
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "returncode": e.returncode,
            "stdout": e.stdout.strip() if e.stdout else "",
            "stderr": e.stderr.strip() if e.stderr else "",
            "error": str(e)
        }

def list_containers():
    """List all Docker containers with detailed information."""
    # Format output as JSON for easier parsing
    cmd = "docker ps -a --format '{{json .}}'"
    result = run_command(cmd)
    
    if not result["success"]:
        return {
            "success": False,
            "message": "Failed to list containers",
            "error": result["stderr"] or result["error"]
        }
    
    # Parse the JSON output
    try:
        # Handle the output which has one JSON object per line
        containers = []
        for line in result["stdout"].splitlines():
            if line.strip():
                container = json.loads(line)
                containers.append(container)
                
        return {
            "success": True,
            "message": f"Found {len(containers)} containers",
            "data": {"containers": containers}
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "message": "Failed to parse container data",
            "error": str(e),
            "raw_output": result["stdout"]
        }

def inspect_container(container_id):
    """Get detailed information about a specific container."""
    if not container_id:
        return {
            "success": False,
            "message": "No container ID provided"
        }
    
    cmd = f"docker inspect {container_id}"
    result = run_command(cmd)
    
    if not result["success"]:
        return {
            "success": False,
            "message": f"Failed to inspect container {container_id}",
            "error": result["stderr"] or result["error"]
        }
    
    try:
        # Parse the JSON output
        inspect_data = json.loads(result["stdout"])
        
        return {
            "success": True,
            "message": f"Container {container_id} inspection completed",
            "data": {"inspection": inspect_data}
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "message": f"Failed to parse inspection data for {container_id}",
            "error": str(e),
            "raw_output": result["stdout"]
        }

def get_container_stats(container_id):
    """Get real-time stats for a container."""
    if not container_id:
        return {
            "success": False,
            "message": "No container ID provided"
        }
    
    # Get a single stats snapshot with JSON format
    cmd = f"docker stats {container_id} --no-stream --format '{{{{json .}}}}'"
    result = run_command(cmd)
    
    if not result["success"]:
        return {
            "success": False,
            "message": f"Failed to get stats for container {container_id}",
            "error": result["stderr"] or result["error"]
        }
    
    try:
        # Parse the JSON output
        stats_data = json.loads(result["stdout"])
        
        return {
            "success": True,
            "message": f"Container {container_id} stats retrieved",
            "data": {"stats": stats_data}
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "message": f"Failed to parse stats data for {container_id}",
            "error": str(e),
            "raw_output": result["stdout"]
        }

def main():
    """Main function to handle input and execute operations."""
    # Check if we have input on stdin
    if not sys.stdin.isatty():
        # Read JSON input from stdin
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            result = {
                "success": False,
                "message": "Invalid JSON input"
            }
            print(json.dumps(result))
            sys.exit(1)
    else:
        # No input
        input_data = {}
    
    # Get the operation to perform
    operation = input_data.get("operation", "list")
    container_id = input_data.get("container_id", "")
    
    # Execute the requested operation
    if operation == "list":
        result = list_containers()
    elif operation == "inspect":
        result = inspect_container(container_id)
    elif operation == "stats":
        result = get_container_stats(container_id)
    else:
        result = {
            "success": False,
            "message": f"Unknown operation: {operation}",
            "available_operations": ["list", "inspect", "stats"]
        }
    
    # Output the result as JSON
    print(json.dumps(result))

if __name__ == "__main__":
    main()