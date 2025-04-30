#!/usr/bin/env python3
"""
Test script to verify that endpoints disabled via environment variables
return 404 Not Found.

This script starts a temporary backend server on a separate port
with specific endpoints disabled.
"""

import os
import sys
import time
import requests
import json
import subprocess
import signal
from pathlib import Path
from datetime import datetime

# --- Configuration ---
# Get the directory of this script
SCRIPT_DIR = Path(__file__).resolve().parent
# Path to the main backend app.py
APP_PATH = SCRIPT_DIR.parent / "app.py"
# Port for the temporary test server
TEST_PORT = 5001
# Base URL for the test server
TEST_BASE_URL = f"http://localhost:{TEST_PORT}"
# Time to wait for the server to start (seconds)
SERVER_START_WAIT = 7 # Increased wait time
# Timeout for API requests (seconds)
REQUEST_TIMEOUT = 5
# Log file path
LOG_FILE = SCRIPT_DIR / "test_endpoint_disabling_results.log"

# Endpoints and their corresponding disable environment variables
# Format: (endpoint_path, http_method, env_variable_name)
ENDPOINTS_TO_DISABLE = [
    ("/api/system", "GET", "ENABLE_SYSTEM_ENDPOINT"),
    ("/api/docker", "GET", "ENABLE_DOCKER_ENDPOINT"),
    ("/api/execute", "POST", "ENABLE_COMMAND_ENDPOINT"),
    ("/api/scripts", "GET", "ENABLE_SCRIPTS_ENDPOINT"),
    # Specific script execution - POST to /api/scripts/<name> is handled by the same route
    # We test the base /api/scripts GET above, which is sufficient for route registration check
    ("/api/processes", "GET", "ENABLE_PROCESSES_ENDPOINT"),
    # Specific process GET - /api/processes/<id> is handled by the same route
    ("/api/control/shutdown", "POST", "ENABLE_CONTROL_ENDPOINT"),
    ("/api/control/reboot", "POST", "ENABLE_CONTROL_ENDPOINT"),
]

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

# --- Logging ---
def init_log_file():
    with open(LOG_FILE, 'w') as f:
        f.write(f"Endpoint Disabling Test Results\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")

def log(message, level="INFO", color=None):
    log_msg = f"[{level}] {message}"
    console_msg = f"{color}[{level}]{Colors.ENDC} {message}" if color else log_msg
    print(console_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + "\n")

# --- Test Functions ---
def start_test_server():
    """Starts the backend server as a subprocess with endpoints disabled."""
    log(f"Starting temporary backend server on port {TEST_PORT}...", color=Colors.YELLOW)
    
    # Prepare environment variables to disable endpoints
    env = os.environ.copy()
    for _, _, env_var in ENDPOINTS_TO_DISABLE:
        env[env_var] = "false"
        log(f"  Disabling via {env_var}=false", level="DEBUG")
        
    # Set the PORT environment variable for the Flask app
    env["PORT"] = str(TEST_PORT)
    log(f"  Setting PORT={TEST_PORT}", level="DEBUG")
    
    # Command to run the Flask app
    # Use sys.executable to ensure the same Python interpreter is used
    command = [sys.executable, str(APP_PATH)] 
    
    try:
        # Start the server process
        # Use preexec_fn=os.setsid to create a new process group, making it easier to kill
        process = subprocess.Popen(
            command, 
            env=env, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid  # Create a new session
        )
        log(f"Server process started (PID: {process.pid}). Waiting {SERVER_START_WAIT}s for it to initialize...", color=Colors.CYAN)
        
        # Wait for the server to start
        time.sleep(SERVER_START_WAIT)
        
        # Check if the server is responding at the root URL
        server_responded = False
        try:
            # Use the root URL which should always exist, even if it gives 404 or other status
            response = requests.get(f"{TEST_BASE_URL}/", timeout=2)
            log(f"Server responded with status code {response.status_code}.", color=Colors.GREEN)
            server_responded = True
            return process
        except requests.exceptions.ConnectionError:
            log("Server did not respond to connection attempt.", "ERROR", Colors.RED)
        except requests.exceptions.Timeout:
            log("Server connection attempt timed out.", "ERROR", Colors.RED)
        except Exception as req_err:
            log(f"Error checking server response: {req_err}", "ERROR", Colors.RED)
            
        # If server did not respond properly
        if not server_responded:
            log("Attempting to terminate unresponsive server process...", "WARN", Colors.YELLOW)
            # Try to capture stderr before terminating
            try:
                stdout, stderr = process.communicate(timeout=1) # Try to get output
                if stderr:
                    log("--- Server Stderr (Potential Startup Error) ---", "DEBUG")
                    log(stderr, "DEBUG")
                    log("------------------------------------------------", "DEBUG")
                if stdout:
                    log("--- Server Stdout ---", "DEBUG")
                    log(stdout, "DEBUG")
                    log("---------------------", "DEBUG")
            except subprocess.TimeoutExpired:
                log("Could not get server output before termination timeout.", "DEBUG")
            except Exception as comm_err:
                log(f"Error getting server output: {comm_err}", "DEBUG")
                
            # Terminate the process
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM) # Kill the process group
                process.wait(timeout=5)
                log("Unresponsive server process terminated.", "WARN", Colors.YELLOW)
            except Exception as e:
                log(f"Error terminating unresponsive server process: {e}", "WARN", Colors.YELLOW)
            return None
            
    except Exception as e:
        log(f"Failed to start server process: {e}", "ERROR", Colors.RED)
        return None

def stop_test_server(process):
    """Stops the test server subprocess."""
    if process:
        log(f"Stopping temporary server (PID: {process.pid})...", color=Colors.YELLOW)
        try:
            # Send SIGTERM to the entire process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5) # Wait for graceful shutdown
            log("Server process terminated.", color=Colors.GREEN)
        except ProcessLookupError:
             log("Server process already stopped.", "WARN", Colors.YELLOW)
        except subprocess.TimeoutExpired:
            log("Server did not stop gracefully, sending SIGKILL...", "WARN", Colors.YELLOW)
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL) # Force kill
                process.wait(timeout=2)
                log("Server process killed.", color=Colors.YELLOW)
            except Exception as kill_err:
                 log(f"Error force killing server process: {kill_err}", "ERROR", Colors.RED)
        except Exception as e:
            log(f"Error stopping server process: {e}", "ERROR", Colors.RED)
        finally:
            # Read remaining output/error streams
            try:
                stdout, stderr = process.communicate(timeout=1)
                if stdout:
                    log("Server stdout:", level="DEBUG")
                    log(stdout, level="DEBUG")
                if stderr:
                    log("Server stderr:", level="DEBUG")
                    log(stderr, level="DEBUG")
            except Exception:
                pass # Ignore errors during cleanup reading

def run_disabled_tests():
    """Runs tests against the temporary server to check for 404s."""
    log("Running tests for disabled endpoints...", color=Colors.CYAN)
    results = []
    
    for endpoint, method, env_var in ENDPOINTS_TO_DISABLE:
        url = f"{TEST_BASE_URL}{endpoint}"
        test_desc = f"Test {method} {endpoint} (disabled by {env_var})"
        log(f"  {test_desc}", "TEST")
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=REQUEST_TIMEOUT)
            elif method.upper() == "POST":
                 # Send empty JSON for POST requests to avoid potential 400 errors for missing body
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json={}, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                log(f"Unsupported HTTP method '{method}' for testing.", "WARN", Colors.YELLOW)
                results.append(False)
                continue

            # Accept either 404 or 405 as success for a disabled endpoint
            if response.status_code in [404, 405]:
                log(f"    PASSED: Received {response.status_code} as expected for disabled endpoint.", "SUCCESS", Colors.GREEN)
                results.append(True)
            else:
                log(f"    FAILED: Expected status code 404 or 405, but got {response.status_code}.", "ERROR", Colors.RED)
                log(f"    Response: {response.text[:200]}...", "DEBUG") # Log beginning of response
                results.append(False)
                
        except requests.exceptions.RequestException as e:
            log(f"    FAILED: Request error during test: {e}", "ERROR", Colors.RED)
            results.append(False)
            
    return all(results)

# --- Main Execution ---
if __name__ == "__main__":
    init_log_file()
    log("Starting Endpoint Disabling Test Suite", color=Colors.BOLD + Colors.CYAN)
    
    server_process = start_test_server()
    
    overall_success = False
    if server_process:
        try:
            overall_success = run_disabled_tests()
        finally:
            # Ensure server is stopped even if tests fail
            stop_test_server(server_process)
    else:
        log("Cannot run tests because the server failed to start.", "ERROR", Colors.RED)

    log("="*70, color=Colors.CYAN)
    if overall_success:
        log("All disabled endpoint tests PASSED!", "RESULT", Colors.BOLD + Colors.GREEN)
        sys.exit(0)
    else:
        log("Some disabled endpoint tests FAILED.", "RESULT", Colors.BOLD + Colors.RED)
        sys.exit(1)

