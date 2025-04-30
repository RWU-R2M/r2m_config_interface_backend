from flask import Blueprint, jsonify, request, current_app
from flask_restful import Resource
from app.utils import get_system_stats, get_docker_containers, execute_command
from app.utils import load_script_configs, execute_script, list_available_scripts
from app.utils import get_process_status, list_running_processes, get_network_stats
from app.utils import start_docker_container, stop_docker_container, restart_docker_container
from app.utils import validate_script_input  # <-- import the new function
import logging
import shlex
import os

logger = logging.getLogger(__name__)

# Create Blueprint for API routes
api_bp = Blueprint('api', __name__)

class StatusAPI(Resource):
    """API resource for the status endpoint"""
    def get(self):
        from datetime import datetime
        return {
            "status": "running",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "REST API server is running"
        }

class SystemStatsAPI(Resource):
    def get(self):
        """Endpoint to get system statistics"""
        try:
            stats = get_system_stats()
            return stats
        except Exception as e:
            logger.error(f"Error in SystemStatsAPI: {str(e)}")
            return {"error": str(e)}, 500

class NetworkStatsAPI(Resource):
    """API endpoint to get network statistics only"""
    def get(self):
        """Get network interface statistics"""
        try:
            stats = get_network_stats()
            return {"network": stats}
        except Exception as e:
            logger.error(f"Error in NetworkStatsAPI: {str(e)}")
            return {"error": str(e)}, 500

class DockerAPI(Resource):
    def get(self):
        """Endpoint to get Docker container information"""
        try:
            containers = get_docker_containers()
            return containers
        except Exception as e:
            logger.error(f"Error in DockerAPI: {str(e)}")
            return {"error": str(e)}, 500

# Add new resources for Docker container actions
class DockerStartAPI(Resource):
    def post(self, container_id):
        """Endpoint to start a Docker container"""
        try:
            result = start_docker_container(container_id)
            if result.get('success', False):
                return result
            else:
                return result, 500 # Return 500 if command failed
        except Exception as e:
            logger.error(f"Error starting container {container_id}: {str(e)}")
            return {"error": str(e)}, 500

class DockerStopAPI(Resource):
    def post(self, container_id):
        """Endpoint to stop a Docker container"""
        try:
            result = stop_docker_container(container_id)
            if result.get('success', False):
                return result
            else:
                return result, 500 # Return 500 if command failed
        except Exception as e:
            logger.error(f"Error stopping container {container_id}: {str(e)}")
            return {"error": str(e)}, 500

class DockerRestartAPI(Resource):
    def post(self, container_id):
        """Endpoint to restart a Docker container"""
        try:
            result = restart_docker_container(container_id)
            if result.get('success', False):
                return result
            else:
                return result, 500 # Return 500 if command failed
        except Exception as e:
            logger.error(f"Error restarting container {container_id}: {str(e)}")
            return {"error": str(e)}, 500

class CommandAPI(Resource):
    def post(self):
        """
        Endpoint to execute system commands
        
        Expects JSON with:
        {
            "command": "command to execute",
            "timeout": optional timeout in seconds (default: 30)
        }
        """
        try:
            if not request.is_json:
                return {"error": "Request must be JSON"}, 400
                
            data = request.get_json()
            
            if not data or 'command' not in data:
                return {"error": "command parameter is required"}, 400
            
            command_str = data['command']
            requested_timeout = data.get('timeout', 30)
            
            # Parse command to get the base command (first word)
            try:
                # Use shlex.split to properly handle quoted arguments
                command_parts = shlex.split(command_str)
                if not command_parts:
                    return {"error": "Empty command"}, 400
                
                base_command = command_parts[0]
            except Exception as e:
                logger.error(f"Error parsing command: {str(e)}")
                return {"error": f"Invalid command format: {str(e)}"}, 400
            
            # Check if the command is in the whitelist (if whitelist is configured)
            whitelist = current_app.config.get('COMMAND_WHITELIST', [])
            if whitelist and base_command not in whitelist:
                logger.warning(f"Blocked execution of non-whitelisted command: {base_command}")
                return {
                    "error": f"Command '{base_command}' is not allowed. Allowed commands: {', '.join(whitelist)}"
                }, 403
            
            # Enforce maximum timeout
            max_timeout = current_app.config.get('COMMAND_MAX_TIMEOUT', 60)
            timeout = min(requested_timeout, max_timeout)
            
            # Execute the command with security checks
            result = execute_command(command_str, timeout)
            
            return result
        except Exception as e:
            logger.error(f"Error in CommandAPI: {str(e)}")
            return {"error": str(e)}, 500

class ScriptsListAPI(Resource):
    """API endpoint to list available custom scripts"""
    def get(self):
        """Get a list of all available scripts and their configurations"""
        try:
            scripts = list_available_scripts()
            return {"scripts": scripts}
        except Exception as e:
            logger.error(f"Error in ScriptsListAPI: {str(e)}")
            return {"error": str(e)}, 500

class ScriptExecuteAPI(Resource):
    """API endpoint to execute a custom script by name"""
    def post(self, script_name):
        """
        Execute a custom script by name
        
        Args:
            script_name: The name of the script to execute
            
        Expects optional JSON with input data (if the script accepts input)
        """
        try:
            # Load script configurations
            script_configs = load_script_configs()
            # Check if the requested script exists
            if script_name not in script_configs:
                return {"error": f"Script '{script_name}' not found"}, 404
            script_config = script_configs[script_name]
            # Check if the script accepts input and if we received any
            accepts_input = script_config.get('accepts_input', False)
            input_data = None
            if accepts_input:
                if request.is_json:
                    input_data = request.get_json()
                elif request.content_length and request.content_length > 0:
                    return {"error": "Request body must be JSON when providing input to script"}, 400
                # --- Parameter validation ---
                input_schema = script_config.get('input_schema')
                valid, error_msg = validate_script_input(input_schema, input_data or {})
                if not valid:
                    return {"error": error_msg}, 400
            
            # Get timeout from request or use default
            requested_timeout = request.args.get('timeout', 30, type=int)
            max_timeout = current_app.config.get('SCRIPT_MAX_TIMEOUT', 60)
            timeout = min(requested_timeout, max_timeout)
            
            # Execute the script
            result = execute_script(script_config, input_data, timeout)
            
            # Return the result
            if result.get('success', False):
                # Make sure we return a JSON serializable object
                if 'output' in result and isinstance(result['output'], dict):
                    return result  # Remove jsonify()
                else:
                    return {       # Remove jsonify()
                        "script": result.get('script', script_name),
                        "success": result.get('success', False),
                        "message": result.get('message', ''),
                        "returncode": result.get('returncode', 0),
                        "output": result.get('output', {}),
                        "process_id": result.get('process_id', None),
                        "async": result.get('async', False)
                    }
            else:
                status_code = 500 if 'error' in result else 400
                return result, status_code  # Remove jsonify()
                
        except Exception as e:
            logger.error(f"Error in ScriptExecuteAPI: {str(e)}")
            return {"error": str(e)}, 500

class ProcessStatusAPI(Resource):
    """API endpoint to get the status of a process"""
    def get(self, process_id):
        """
        Get the status of a process
        
        Args:
            process_id: The process ID to check
        """
        try:
            status = get_process_status(process_id)
            
            if status.get('success', False):
                return status
            else:
                return status, 404
                
        except Exception as e:
            logger.error(f"Error in ProcessStatusAPI: {str(e)}")
            return {"error": str(e)}, 500

class ProcessListAPI(Resource):
    """API endpoint to list all tracked processes"""
    def get(self):
        """Get a list of all tracked processes and their status"""
        try:
            processes = list_running_processes()
            return {"processes": processes}
        except Exception as e:
            logger.error(f"Error in ProcessListAPI: {str(e)}")
            return {"error": str(e)}, 500

# --- Add Shutdown and Reboot API Resources ---
class ShutdownAPI(Resource):
    def post(self):
        """Endpoint to shut down the system"""
        try:
            # SECURITY WARNING: This command has significant system impact.
            # Ensure this endpoint is properly secured in a production environment.
            logger.warning("Received request to SHUT DOWN the system.")
            # Use '-h' for halt/power off, adjust if needed (e.g., '-r' for reboot)
            # Add 'sudo' if the backend doesn't run as root and needs privileges
            # result = execute_command('sudo shutdown -h now', timeout=10) 
            result = execute_command('shutdown -h now', timeout=10) # Assuming backend runs with sufficient privileges
            if result.get('success', False):
                return {"message": "Shutdown command initiated successfully."}
            else:
                # Log the specific error from execute_command
                error_detail = result.get('error', result.get('stderr', 'Unknown execution error'))
                logger.error(f"Shutdown command failed: {error_detail}")
                return {"error": "Failed to initiate shutdown.", "details": error_detail}, 500
        except Exception as e:
            logger.error(f"Error in ShutdownAPI: {str(e)}")
            return {"error": str(e)}, 500

class RebootAPI(Resource):
    def post(self):
        """Endpoint to reboot the system"""
        try:
            # SECURITY WARNING: This command has significant system impact.
            # Ensure this endpoint is properly secured in a production environment.
            logger.warning("Received request to REBOOT the system.")
            # Add 'sudo' if the backend doesn't run as root and needs privileges
            # result = execute_command('sudo reboot', timeout=10)
            result = execute_command('reboot', timeout=10) # Assuming backend runs with sufficient privileges
            if result.get('success', False):
                return {"message": "Reboot command initiated successfully."}
            else:
                # Log the specific error from execute_command
                error_detail = result.get('error', result.get('stderr', 'Unknown execution error'))
                logger.error(f"Reboot command failed: {error_detail}")
                return {"error": "Failed to initiate reboot.", "details": error_detail}, 500
        except Exception as e:
            logger.error(f"Error in RebootAPI: {str(e)}")
            return {"error": str(e)}, 500
# --- End of Shutdown and Reboot API Resources ---

# Function to get API resources with env var configuration
def get_api_resources():
    """Get API resources with configuration from environment variables"""
    import os
    
    # Determine which endpoints are enabled via environment variables
    enable_status = os.environ.get('ENABLE_STATUS_ENDPOINT', 'true').lower() == 'true'
    enable_system = os.environ.get('ENABLE_SYSTEM_ENDPOINT', 'true').lower() == 'true'
    enable_docker = os.environ.get('ENABLE_DOCKER_ENDPOINT', 'true').lower() == 'true'
    enable_command = os.environ.get('ENABLE_COMMAND_ENDPOINT', 'true').lower() == 'true'
    enable_scripts = os.environ.get('ENABLE_SCRIPTS_ENDPOINT', 'true').lower() == 'true'
    enable_processes = os.environ.get('ENABLE_PROCESSES_ENDPOINT', 'true').lower() == 'true'
    # Add a flag for control endpoints, default to true
    enable_control = os.environ.get('ENABLE_CONTROL_ENDPOINT', 'true').lower() == 'true'
    
    # Create resources list with enabled flag
    resources = [
        {'resource': StatusAPI, 'endpoint': '/', 'enabled': enable_status},
        {'resource': SystemStatsAPI, 'endpoint': '/api/system', 'enabled': enable_system},
        {'resource': NetworkStatsAPI, 'endpoint': '/api/system/network', 'enabled': enable_system},
        {'resource': DockerAPI, 'endpoint': '/api/docker', 'enabled': enable_docker},
        # Add the new Docker action endpoints
        {'resource': DockerStartAPI, 'endpoint': '/api/docker/<string:container_id>/start', 'enabled': enable_docker},
        {'resource': DockerStopAPI, 'endpoint': '/api/docker/<string:container_id>/stop', 'enabled': enable_docker},
        {'resource': DockerRestartAPI, 'endpoint': '/api/docker/<string:container_id>/restart', 'enabled': enable_docker},
        {'resource': CommandAPI, 'endpoint': '/api/execute', 'enabled': enable_command},
        {'resource': ScriptsListAPI, 'endpoint': '/api/scripts', 'enabled': enable_scripts},
        {'resource': ScriptExecuteAPI, 'endpoint': '/api/scripts/<string:script_name>', 'enabled': enable_scripts},
        {'resource': ProcessStatusAPI, 'endpoint': '/api/processes/<string:process_id>', 'enabled': enable_processes},
        {'resource': ProcessListAPI, 'endpoint': '/api/processes', 'enabled': enable_processes},
        # Add the new control endpoints
        {'resource': ShutdownAPI, 'endpoint': '/api/control/shutdown', 'enabled': enable_control},
        {'resource': RebootAPI, 'endpoint': '/api/control/reboot', 'enabled': enable_control}
    ]
    
    return resources