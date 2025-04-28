from flask import Blueprint, jsonify, request, current_app
from flask_restful import Resource
from app.utils import get_system_stats, get_docker_containers, execute_command
from app.utils import load_script_configs, execute_script, list_available_scripts
from app.utils import get_process_status, list_running_processes
import logging
import shlex

logger = logging.getLogger(__name__)

# Create Blueprint for API routes
api_bp = Blueprint('api', __name__)

class StatusAPI(Resource):
    """API resource for the status endpoint"""
    def get(self):
        from datetime import datetime
        return jsonify({
            "status": "running",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "REST API server is running"
        })

class SystemStatsAPI(Resource):
    def get(self):
        """Endpoint to get system statistics"""
        try:
            stats = get_system_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error in SystemStatsAPI: {str(e)}")
            return jsonify({"error": str(e)}), 500

class DockerAPI(Resource):
    def get(self):
        """Endpoint to get Docker container information"""
        try:
            containers = get_docker_containers()
            return jsonify(containers)
        except Exception as e:
            logger.error(f"Error in DockerAPI: {str(e)}")
            return jsonify({"error": str(e)}), 500

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
                return jsonify({"error": "Request must be JSON"}), 400
                
            data = request.get_json()
            
            if not data or 'command' not in data:
                return jsonify({"error": "command parameter is required"}), 400
            
            command_str = data['command']
            requested_timeout = data.get('timeout', 30)
            
            # Parse command to get the base command (first word)
            try:
                # Use shlex.split to properly handle quoted arguments
                command_parts = shlex.split(command_str)
                if not command_parts:
                    return jsonify({"error": "Empty command"}), 400
                
                base_command = command_parts[0]
            except Exception as e:
                logger.error(f"Error parsing command: {str(e)}")
                return jsonify({"error": f"Invalid command format: {str(e)}"}), 400
            
            # Check if the command is in the whitelist (if whitelist is configured)
            whitelist = current_app.config.get('COMMAND_WHITELIST', [])
            if whitelist and base_command not in whitelist:
                logger.warning(f"Blocked execution of non-whitelisted command: {base_command}")
                return jsonify({
                    "error": f"Command '{base_command}' is not allowed. Allowed commands: {', '.join(whitelist)}"
                }), 403
            
            # Enforce maximum timeout
            max_timeout = current_app.config.get('COMMAND_MAX_TIMEOUT', 60)
            timeout = min(requested_timeout, max_timeout)
            
            # Execute the command with security checks
            result = execute_command(command_str, timeout)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in CommandAPI: {str(e)}")
            return jsonify({"error": str(e)}), 500

class ScriptsListAPI(Resource):
    """API endpoint to list available custom scripts"""
    def get(self):
        """Get a list of all available scripts and their configurations"""
        try:
            scripts = list_available_scripts()
            return jsonify({"scripts": scripts})
        except Exception as e:
            logger.error(f"Error in ScriptsListAPI: {str(e)}")
            return jsonify({"error": str(e)}), 500

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
                return jsonify({"error": f"Script '{script_name}' not found"}), 404
            
            script_config = script_configs[script_name]
            
            # Check if the script accepts input and if we received any
            accepts_input = script_config.get('accepts_input', False)
            input_data = None
            
            if accepts_input:
                if request.is_json:
                    input_data = request.get_json()
                elif request.content_length and request.content_length > 0:
                    return jsonify({"error": "Request body must be JSON when providing input to script"}), 400
            
            # Get timeout from request or use default
            requested_timeout = request.args.get('timeout', 30, type=int)
            max_timeout = current_app.config.get('SCRIPT_MAX_TIMEOUT', 60)
            timeout = min(requested_timeout, max_timeout)
            
            # Execute the script
            result = execute_script(script_config, input_data, timeout)
            
            # Return the result
            if result.get('success', False):
                # Make sure we return a JSON serializable object
                serializable_result = dict(result)
                # If there's a response object that cannot be serialized, convert it to a string
                if not isinstance(serializable_result, dict):
                    return jsonify({
                        "error": "Result is not a valid dictionary",
                        "success": False
                    }), 500
                
                return jsonify(serializable_result)
            else:
                status_code = 500 if 'error' in result else 400
                return jsonify(result), status_code
                
        except Exception as e:
            logger.error(f"Error in ScriptExecuteAPI: {str(e)}")
            return jsonify({"error": str(e)}), 500

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
                return jsonify(status)
            else:
                return jsonify(status), 404
                
        except Exception as e:
            logger.error(f"Error in ProcessStatusAPI: {str(e)}")
            return jsonify({"error": str(e)}), 500

class ProcessListAPI(Resource):
    """API endpoint to list all tracked processes"""
    def get(self):
        """Get a list of all tracked processes and their status"""
        try:
            processes = list_running_processes()
            return jsonify({"processes": processes})
        except Exception as e:
            logger.error(f"Error in ProcessListAPI: {str(e)}")
            return jsonify({"error": str(e)}), 500

# Define API resources to be registered in main app.py
api_resources = [
    (SystemStatsAPI, '/api/system'),
    (DockerAPI, '/api/docker'),
    (CommandAPI, '/api/execute'),
    (ScriptsListAPI, '/api/scripts'),
    (ScriptExecuteAPI, '/api/scripts/<string:script_name>'),
    (ProcessStatusAPI, '/api/processes/<string:process_id>'),
    (ProcessListAPI, '/api/processes')
]