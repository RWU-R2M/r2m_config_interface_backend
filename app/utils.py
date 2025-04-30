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
import jsonschema # Import jsonschema for validation

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
def validate_script_config(config, config_file_path):
    """
    Validate that a script configuration adheres to the defined standard.

    Args:
        config: The script configuration dictionary to validate.
        config_file_path: The path to the config file (for logging).

    Returns:
        Boolean indicating whether the configuration is valid.
    """
    # Define the standard fields and their expected types
    standard_fields = {
        'name': str,
        'description': str,
        'script_path': str,
        'endpoint': str,
        'accepts_input': bool,
        'input_method': str, # Should be 'json' or 'env'
        'async': bool,
    }

    # 1. Check for missing standard fields
    for field in standard_fields:
        if field not in config:
            logger.error(f"Invalid config in {config_file_path}: Missing required field '{field}'.")
            return False

    # 2. Check types of standard fields
    for field, expected_type in standard_fields.items():
        if not isinstance(config[field], expected_type):
            logger.error(f"Invalid config in {config_file_path}: Field '{field}' should be type {expected_type.__name__}, but got {type(config[field]).__name__}.")
            return False

    # 3. Validate specific field values
    if config['input_method'] not in ['json', 'env']:
        logger.error(f"Invalid config in {config_file_path}: Field 'input_method' must be 'json' or 'env', but got '{config['input_method']}'.")
        return False

    # 4. Conditional validation for input_schema
    if config['accepts_input']:
        if 'input_schema' not in config:
            logger.warning(f"Config warning in {config_file_path}: Script '{config['name']}' accepts input but does not define 'input_schema'.")
        elif not isinstance(config['input_schema'], dict):
             logger.error(f"Invalid config in {config_file_path}: Field 'input_schema' must be a dictionary (JSON Schema object), but got {type(config['input_schema']).__name__}.")
             return False

    # 5. Conditional validation for expected_output (for synchronous scripts)
    if not config['async']:
        if 'expected_output' not in config:
            logger.warning(f"Config warning in {config_file_path}: Synchronous script '{config['name']}' does not define 'expected_output'.")
        elif not isinstance(config['expected_output'], (dict, str)):
             logger.error(f"Invalid config in {config_file_path}: Field 'expected_output' must be a dictionary or a string, but got {type(config['expected_output']).__name__}.")
             return False

    # 6. Validate that the script file exists
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    script_path = os.path.join(script_dir, config['script_path'])

    if not os.path.exists(script_path):
        logger.error(f"Invalid config in {config_file_path}: Script file not found at '{script_path}' (relative to {script_dir}).")
        return False

    # 7. Check for unknown fields (optional, makes it stricter)
    allowed_fields = set(standard_fields.keys()) | {'input_schema', 'expected_output'}
    for key in config:
        if key not in allowed_fields:
            logger.warning(f"Config warning in {config_file_path}: Unknown field '{key}' found in script '{config['name']}'.")

    return True

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
                
                # Validate the config against the stricter standard
                # Pass the config file path for better logging
                if not validate_script_config(config, config_file):
                    # Log message is handled within validate_script_config
                    continue # Skip this invalid config

                script_name = config['name']
                script_configs[script_name] = config
                logger.info(f"Loaded script configuration for '{script_name}' from {config_file.name}")
        except Exception as e:
            logger.error(f"Error loading script configuration from {config_file}: {str(e)}")
    
    return script_configs

def validate_script_input(input_schema, input_data):
    """
    Validate input_data against the input_schema from the script config using jsonschema.
    Returns (True, None) if valid, (False, error_message) if invalid.
    """
    if not input_schema:
        # If accepts_input is true but no schema is defined, allow any input.
        # Validation logic in validate_script_config handles warnings/errors for missing schema.
        return True, None

    # Ensure input_data is a dictionary if schema expects an object
    if input_schema.get('type') == 'object' and input_data is None:
        input_data = {} # Treat null input as empty object for validation

    try:
        # Use jsonschema library for robust validation
        jsonschema.validate(instance=input_data, schema=input_schema)
        return True, None
    except jsonschema.ValidationError as e:
        # Provide a user-friendly error message
        error_path = " -> ".join(map(str, e.path))
        error_msg = f"Input validation failed for field '{error_path}': {e.message}" if e.path else f"Input validation failed: {e.message}"
        logger.warning(f"Script input validation error: {error_msg} (Schema: {input_schema}, Data: {input_data})")
        return False, error_msg
    except jsonschema.SchemaError as e:
        # This indicates an invalid schema in the config file itself
        logger.error(f"Invalid input_schema detected during validation: {e}")
        return False, "Server configuration error: Invalid input schema defined for this script."
    except Exception as e:
        # Catch unexpected errors during validation
        logger.error(f"Unexpected error during input validation: {e}")
        return False, f"An unexpected error occurred during input validation: {e}"

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
                    # input is bytes, so text=False (default)
                    result = subprocess.run(
                        command,
                        input=stdin_data,
                        env=env,
                        capture_output=True,
                        timeout=timeout
                    )
                    # Manually decode stdout/stderr since text=False
                    stdout_str = result.stdout.decode() if result.stdout else ''
                    stderr_str = result.stderr.decode() if result.stderr else ''
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
                # For synchronous scripts without input, text=True is fine
                result = subprocess.run(
                    command,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                # stdout/stderr are already strings due to text=True
                stdout_str = result.stdout
                stderr_str = result.stderr
        
        # If we reached here, we're in a synchronous script execution path
        # and should have a result object
        
        # Use the decoded stdout string
        output = stdout_str.strip()
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
                    "stderr": stderr_str, # Use decoded stderr
                    "success": False
                }
        else: # Handle as plain text
            parsed_output = output

        # Return result
        return {
            "script": script_config['name'],
            "returncode": result.returncode,
            "output": parsed_output, # Use the parsed output (JSON or text)
            "stderr": stderr_str, # Use decoded stderr
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
            'name': config.get('name'), # Use .get() as validation now happens earlier
            'description': config.get('description'),
            'endpoint': config.get('endpoint'),
            'accepts_input': config.get('accepts_input', False),
            'async': config.get('async', False),
            # Include input_schema and expected_output if they exist
            'input_schema': config.get('input_schema'),
            'expected_output': config.get('expected_output')
        }
        # Remove keys with None values if they were missing in the original valid config
        safe_config = {k: v for k, v in safe_config.items() if v is not None}

        safe_configs.append(safe_config)

    return safe_configs