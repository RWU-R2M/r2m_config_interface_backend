import subprocess
import json
import logging
# Use dict.get(key, default) for accessing dictionary keys that might not exist
# to avoid KeyError exceptions and provide sensible defaults.
import psutil
import os
import glob
import yaml
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Terminal State ---
# WARNING: This global variable approach assumes a single user/session for the terminal.
# For multi-user support, this state would need to be managed differently (e.g., Flask session).
terminal_cwd = os.getcwd() # Initialize with the backend's starting directory
# ---------------------

# Global dictionary to track running processes
# Keys are process IDs, values are process objects
running_processes = {}
processes_lock = threading.Lock()

def get_system_stats():
    """Get detailed system statistics"""
    try:
        cpu_usage = psutil.cpu_percent(interval=1, percpu=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        stats = {
            "cpu": {
                "total_percent": sum(cpu_usage) / len(cpu_usage),
                "per_core": cpu_usage,
                "cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": get_network_stats()
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return {"error": str(e)}

def get_network_stats():
    """Get network interface statistics"""
    try:
        network_stats = {}
        net_io = psutil.net_io_counters(pernic=True)
        
        for interface, stats in net_io.items():
            network_stats[interface] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv
            }
        
        return network_stats
    except Exception as e:
        logger.error(f"Error getting network stats: {str(e)}")
        return {"error": str(e)}

def get_docker_containers():
    """Get information about Docker containers"""
    try:
        # Use subprocess to call Docker CLI
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{json .}}'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Docker command failed: {result.stderr}")
            return {"error": "Failed to get Docker containers", "details": result.stderr}
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    container_info = json.loads(line)
                    containers.append(container_info)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Docker output: {str(e)}")
        
        return {"containers": containers}
    except Exception as e:
        logger.error(f"Error getting Docker containers: {str(e)}")
        return {"error": str(e)}

# Docker control functions
def start_docker_container(container_id):
    """Start a specific Docker container by ID"""
    return execute_command(f'docker start {container_id}', timeout=60)

def stop_docker_container(container_id):
    """Stop a specific Docker container by ID"""
    return execute_command(f'docker stop {container_id}', timeout=60)

def restart_docker_container(container_id):
    """Restart a specific Docker container by ID"""
    return execute_command(f'docker restart {container_id}', timeout=60)

def execute_command(command_str, timeout=30):
    """
    Execute a shell command with safety precautions, handling 'cd' internally.
    
    Args:
        command_str: Command string to execute
        timeout: Maximum execution time in seconds
        
    Returns:
        Dictionary with command result information
    """
    global terminal_cwd # Need to modify the global variable

    try:
        # SECURITY WARNING: This is for demonstration purposes only
        # In a production environment, you should whitelist allowed commands
        # or use a more secure approach
        
        # Split the command string into arguments
        command_parts = command_str.split()
        if not command_parts:
            return {"command": command_str, "error": "Empty command", "success": False}

        # --- Handle 'cd' command internally --- 
        if command_parts[0] == 'cd':
            if len(command_parts) == 1:
                # 'cd' without arguments - typically goes to home, but let's just stay
                # Or maybe go to the initial CWD? For simplicity, stay.
                target_dir = '.' # Effectively do nothing, or could go to initial CWD
            else:
                target_dir = command_parts[1]
            
            try:
                # Calculate the new path relative to the current virtual CWD
                new_path = os.path.abspath(os.path.join(terminal_cwd, target_dir))
                
                # Check if the new path is a valid directory
                if os.path.isdir(new_path):
                    terminal_cwd = new_path
                    logger.info(f"Changed terminal CWD to: {terminal_cwd}")
                    return {
                        "command": command_str,
                        "returncode": 0,
                        "stdout": f"Changed directory to {terminal_cwd}", # Provide feedback
                        "stderr": "",
                        "success": True
                    }
                else:
                    error_msg = f"cd: no such file or directory: {target_dir}"
                    logger.warning(error_msg)
                    return {
                        "command": command_str,
                        "returncode": 1,
                        "stdout": "",
                        "stderr": error_msg,
                        "success": False
                    }
            except Exception as e:
                error_msg = f"cd: error changing directory: {str(e)}"
                logger.error(error_msg)
                return {
                    "command": command_str,
                    "returncode": 1,
                    "stdout": "",
                    "stderr": error_msg,
                    "success": False
                }
        # --- End of 'cd' handling ---

        # For other commands, execute in a subprocess using the stored CWD
        logger.info(f"Executing command: {' '.join(command_parts)} in CWD: {terminal_cwd}")
        
        # Execute the command with a timeout and the correct CWD
        result = subprocess.run(
            command_parts, # Use the split parts
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=terminal_cwd # Set the current working directory for the subprocess
        )
        
        # Log the results
        logger.info(f"Command '{command_str}' finished with return code: {result.returncode}")
        if result.stdout:
            logger.info(f"Command '{command_str}' stdout:\n{result.stdout}")
        if result.stderr:
            # Log stderr as warning, as some commands use it for non-error info
            logger.warning(f"Command '{command_str}' stderr:\n{result.stderr}")

        return {
            "command": command_str,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command_str,
            "error": f"Command timed out after {timeout} seconds",
            "success": False
        }
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        return {
            "command": command_str,
            "error": str(e),
            "success": False
        }
        
# Script-related utility functions
def load_script_configs():
    """
    Load all script configurations from the config/scripts directory
    
    Returns:
        Dictionary mapping script names to their configuration
    """
    script_configs = {}
    config_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'scripts')))
    
    if not config_dir.exists():
        logger.warning(f"Script config directory not found: {config_dir}")
        return script_configs
    
    # Load all YAML and JSON files in the config directory
    config_files = list(config_dir.glob('*.yaml')) + list(config_dir.glob('*.yml')) + list(config_dir.glob('*.json'))
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
                
                # Validate that the config has the required fields
                if not validate_script_config(config):
                    logger.error(f"Invalid script configuration in {config_file}")
                    continue
                
                script_name = config['name']
                script_configs[script_name] = config
                logger.info(f"Loaded script configuration for '{script_name}' from {config_file.name}")
        except Exception as e:
            logger.error(f"Error loading script configuration from {config_file}: {str(e)}")
    
    return script_configs

def validate_script_config(config):
    """
    Validate that a script configuration has all required fields
    
    Args:
        config: The script configuration to validate
        
    Returns:
        Boolean indicating whether the configuration is valid
    """
    required_fields = ['name', 'script_path', 'endpoint', 'description']
    for field in required_fields:
        if field not in config:
            logger.error(f"Script configuration missing required field: {field}")
            return False
    
    # Validate that the script file exists
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    script_path = os.path.join(script_dir, config['script_path'])
    
    # Check if script exists either directly or in examples directory
    if not os.path.exists(script_path):
        # If not found, try looking in the examples directory if the path specifies it
        if config['script_path'].startswith('examples/'):
            # Script path already includes examples/ prefix, just check if it exists
            if not os.path.exists(script_path):
                logger.error(f"Script file not found: {script_path}")
                return False
        else:
            logger.error(f"Script file not found: {script_path}")
            return False
    
    # If script is synchronous, it should define expected_output fields
    # Use .get() for optional fields like 'async'
    if config.get('async', False) is False and 'expected_output' not in config:
        logger.warning(f"Synchronous script '{config['name']}' does not define expected_output")

    return True

def validate_script_input(input_schema, input_data):
    """
    Validate input_data against the input_schema from the script config.
    Returns (True, None) if valid, (False, error_message) if invalid.
    """
    if not input_schema:
        return True, None  # No schema, accept anything

    # Use .get() with defaults for potentially missing schema keys
    required = input_schema.get('required', [])
    properties = input_schema.get('properties', {})

    # Check for missing required fields
    for key in required:
        if key not in input_data:
            return False, f"Missing required parameter: '{key}'"

    # Check for extra fields
    for key in input_data:
        if key not in properties:
            return False, f"Unexpected parameter: '{key}'"

    # Check types
    type_map = {
        'string': str,
        'integer': int,
        'number': (int, float),
        'boolean': bool
    }
    for key, prop in properties.items():
        if key in input_data:
            # Use .get() for potentially missing 'type' in property definition
            expected_type = prop.get('type')
            if expected_type and expected_type in type_map:
                if not isinstance(input_data[key], type_map[expected_type]):
                    return False, f"Parameter '{key}' should be of type '{expected_type}'"
    return True, None

def execute_script(script_config, input_data=None, timeout=30):
    """
    Execute a script based on its configuration
    
    Args:
        script_config: The script configuration
        input_data: Optional JSON input data for the script
        timeout: Maximum execution time in seconds
        
    Returns:
        Dictionary with script result information
    """
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    script_path = os.path.join(script_dir, script_config['script_path'])
    
    # Determine script type based on file extension
    script_type = os.path.splitext(script_path)[1].lower()
    
    # Determine if this script accepts input parameters (use .get with default False)
    accepts_input = script_config.get('accepts_input', False)
    
    # Determine if the script should run asynchronously (use .get with default False)
    is_async = script_config.get('async', False)
    
    # Prepare environment variables if needed
    env = os.environ.copy()
    
    try:
        # Prepare command based on script type
        if script_type == '.py':
            command = ['python', script_path]
        elif script_type in ['.sh', '.bash']:
            command = ['bash', script_path]
        else:
            # For other types, try to execute directly
            command = [script_path]
        
        # Handle input differently based on sync/async and input method
        if accepts_input and input_data:
            # If using environment variables for input (use .get with default 'json')
            if script_config.get('input_method', 'json') == 'env':
                for key, value in input_data.items():
                    env[key] = str(value)
                
                # For async or env input, no stdin needed
                if is_async:
                    # For asynchronous scripts, start and don't wait
                    process = subprocess.Popen(
                        command,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    # Track the process
                    with processes_lock:
                        running_processes[process.pid] = {
                            'process': process,
                            'name': script_config['name'],
                            'start_time': time.time(),
                            'completed': False,
                            'command': command
                        }
                    
                    # Return immediately with the process ID
                    return {
                        "script": script_config['name'],
                        "process_id": process.pid,
                        "async": True,
                        "message": f"Script '{script_config['name']}' started asynchronously",
                        "success": True
                    }
                else:
                    # For synchronous scripts with env vars, capture output
                    result = subprocess.run(
                        command,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
            else:
                # Using JSON via stdin
                stdin_data = json.dumps(input_data).encode()
                
                if is_async:
                    # For asynchronous scripts with stdin input
                    process = subprocess.Popen(
                        command,
                        env=env,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    # Write to stdin and close it
                    if stdin_data:
                        process.stdin.write(stdin_data)
                        process.stdin.close()
                    
                    # Track the process
                    with processes_lock:
                        running_processes[process.pid] = {
                            'process': process,
                            'name': script_config['name'],
                            'start_time': time.time(),
                            'completed': False,
                            'command': command
                        }
                    
                    # Return immediately with the process ID
                    return {
                        "script": script_config['name'],
                        "process_id": process.pid,
                        "async": True,
                        "message": f"Script '{script_config['name']}' started asynchronously",
                        "success": True
                    }
                else:
                    # For synchronous scripts with stdin input
                    result = subprocess.run(
                        command,
                        input=stdin_data,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
        else:
            # Script doesn't accept input or no input provided
            if is_async:
                # For asynchronous scripts without input
                process = subprocess.Popen(
                    command,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # Track the process
                with processes_lock:
                    running_processes[process.pid] = {
                        'process': process,
                        'name': script_config['name'],
                        'start_time': time.time(),
                        'completed': False,
                        'command': command
                    }
                
                # Return immediately with the process ID
                return {
                    "script": script_config['name'],
                    "process_id": process.pid,
                    "async": True,
                    "message": f"Script '{script_config['name']}' started asynchronously",
                    "success": True
                }
            else:
                # For synchronous scripts without input
                result = subprocess.run(
                    command,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
        
        # If we reached here, we're in a synchronous script execution path
        # and should have a result object
        
        output = result.stdout.strip()
        # Use .get() for optional output_type, defaulting to 'json'
        output_type = script_config.get('output_type', 'json')
        parsed_output = None

        # Try to parse output based on expected type
        if output_type == 'json':
            try:
                if output:
                    parsed_output = json.loads(output)
            except json.JSONDecodeError:
                logger.error(f"Script '{script_config['name']}' output was not valid JSON.")
                return {
                    "error": "Script output is not valid JSON",
                    "script": script_config['name'],
                    "raw_output": output,
                    "stderr": result.stderr,
                    "success": False
                }
        else: # Handle as plain text
            parsed_output = output

        # Return result
        return {
            "script": script_config['name'],
            "returncode": result.returncode,
            "output": parsed_output, # Use the parsed output (JSON or text)
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    except subprocess.TimeoutExpired:
        return {
            "script": script_config['name'],
            "error": f"Script execution timed out after {timeout} seconds",
            "success": False
        }
    except Exception as e:
        logger.error(f"Error executing script '{script_config['name']}': {str(e)}")
        return {
            "script": script_config['name'],
            "error": str(e),
            "success": False
        }

def get_process_status(process_id):
    """
    Get the status of a running or completed process.
    Checks the actual process state if not already marked completed.
    """
    try:
        pid = int(process_id)
        with processes_lock:
            if pid not in running_processes:
                return {
                    "error": f"Process ID {pid} not found or already cleaned up",
                    "success": False
                }

            process_info = running_processes[pid]

            # Check if process is still running and update if it finished
            if not process_info.get('completed', False):
                process = process_info['process']
                returncode = process.poll()
                if returncode is not None:
                    logger.info(f"Process {pid} ({process_info['name']}) detected as completed with return code {returncode} during status check.")
                    process_info['completed'] = True
                    process_info['returncode'] = returncode
                    process_info['end_time'] = time.time()

            # Format runtime duration
            duration = None
            if process_info.get('completed') and 'end_time' in process_info:
                duration = process_info['end_time'] - process_info['start_time']
            elif not process_info.get('completed'):
                duration = time.time() - process_info['start_time']

            # Create response
            status = {
                "script": process_info['name'],
                "process_id": pid,
                "running": not process_info.get('completed', False),
                "start_time": process_info['start_time'],
                "duration": round(duration, 2) if duration is not None else None,
                "success": True
            }

            # Add completion info if available
            if process_info.get('completed'):
                status.update({
                    "completed": True,
                    "returncode": process_info.get('returncode'),
                    "end_time": process_info.get('end_time'),
                    "exit_status": "success" if process_info.get('returncode') == 0 else "error"
                })

            return status

    except Exception as e:
        logger.error(f"Error getting process status for {process_id}: {str(e)}")
        return {
            "error": str(e),
            "success": False
        }

def list_running_processes():
    """
    List all tracked processes, update their status on demand, and clean up old entries.
    """
    process_list = []
    to_remove = []
    now = time.time()
    cleanup_threshold = 3600 # 1 hour

    with processes_lock:
        # First pass: Update status and build list
        for pid, process_info in running_processes.items():
            # Check if process is still running and update if it finished
            if not process_info.get('completed', False):
                process = process_info['process']
                returncode = process.poll()
                if returncode is not None:
                    logger.info(f"Process {pid} ({process_info['name']}) detected as completed with return code {returncode} during list check.")
                    process_info['completed'] = True
                    process_info['returncode'] = returncode
                    process_info['end_time'] = time.time()

            # Format runtime duration
            duration = None
            if process_info.get('completed') and 'end_time' in process_info:
                duration = process_info['end_time'] - process_info['start_time']
                # Check if it's an old completed process eligible for cleanup
                if now - process_info['end_time'] > cleanup_threshold:
                    to_remove.append(pid)
            elif not process_info.get('completed'):
                duration = now - process_info['start_time']

            # Create process status entry for the response list
            status = {
                "script": process_info['name'],
                "process_id": pid,
                "running": not process_info.get('completed', False),
                "start_time": process_info['start_time'],
                "duration": round(duration, 2) if duration is not None else None
            }

            # Add completion info if available
            if process_info.get('completed'):
                status.update({
                    "completed": True,
                    "returncode": process_info.get('returncode'),
                    "end_time": process_info.get('end_time'),
                    "exit_status": "success" if process_info.get('returncode') == 0 else "error"
                })

            process_list.append(status)

        # Second pass: Remove old completed processes
        for pid in to_remove:
            if pid in running_processes: # Check if still exists (should always be true here)
                logger.info(f"Removing completed process {pid} ({running_processes[pid]['name']}) from tracking after timeout during list check.")
                del running_processes[pid]

    return process_list

def list_available_scripts():
    """
    List all available scripts and their configurations
    
    Returns:
        List of script configurations with sensitive data removed
    """
    script_configs = load_script_configs()

    # Remove sensitive information from configs
    safe_configs = []
    for name, config in script_configs.items():
        safe_config = {
            'name': config['name'], # name is required, so [] is okay here
            'description': config['description'], # description is required
            'endpoint': config['endpoint'], # endpoint is required
            # Use .get() for optional fields, providing defaults
            'accepts_input': config.get('accepts_input', False),
            'async': config.get('async', False)
        }

        # Include input_schema if present (use .get)
        input_schema = config.get('input_schema')
        if input_schema:
            safe_config['input_schema'] = input_schema

        # Include expected_output if present (use .get)
        expected_output = config.get('expected_output')
        if expected_output:
            safe_config['expected_output'] = expected_output

        safe_configs.append(safe_config)

    return safe_configs