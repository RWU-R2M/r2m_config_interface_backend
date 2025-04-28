from flask import Flask, jsonify
from flask_restful import Api
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our route modules
from app.routes import api_resources, StatusAPI
from app.utils import load_script_configs

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_enabled(env_var):
    """Check if a feature is enabled via environment variables"""
    return os.environ.get(env_var, 'true').lower() == 'true'

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    api = Api(app)
    
    # Register base status endpoint if enabled
    if is_enabled('ENABLE_STATUS_ENDPOINT'):
        logger.info("Enabling base status endpoint (/)")
        @app.route('/')
        def index():
            return jsonify({
                "status": "running",
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "REST API server is running"
            })
    
    # Create a dict to map API endpoints to their environment variable names
    endpoints_config = {
        '/api/system': 'ENABLE_SYSTEM_ENDPOINT',
        '/api/docker': 'ENABLE_DOCKER_ENDPOINT',
        '/api/execute': 'ENABLE_COMMAND_ENDPOINT',
        '/api/scripts': 'ENABLE_SCRIPTS_ENDPOINT',
        '/api/scripts/<string:script_name>': 'ENABLE_SCRIPTS_ENDPOINT',
        '/api/processes': 'ENABLE_PROCESSES_ENDPOINT',
        '/api/processes/<string:process_id>': 'ENABLE_PROCESSES_ENDPOINT'
    }
    
    # Register API resources based on configuration
    for resource, route in api_resources:
        # Check if the route is in our config map and if it's enabled
        if route in endpoints_config:
            if is_enabled(endpoints_config[route]):
                logger.info(f"Enabling endpoint: {route}")
                api.add_resource(resource, route)
            else:
                logger.info(f"Endpoint disabled by configuration: {route}")
        else:
            # For any routes not in our config map, enable by default
            logger.info(f"Enabling endpoint (not in config): {route}")
            api.add_resource(resource, route)

    # Apply security settings
    # Set command whitelist in app config
    app.config['COMMAND_WHITELIST'] = [
        cmd.strip() for cmd in os.environ.get('COMMAND_WHITELIST', '').split(',') if cmd.strip()
    ]
    
    # Set maximum command timeout
    try:
        app.config['COMMAND_MAX_TIMEOUT'] = int(os.environ.get('COMMAND_MAX_TIMEOUT', 60))
    except ValueError:
        logger.warning("Invalid COMMAND_MAX_TIMEOUT value, using default of 60 seconds")
        app.config['COMMAND_MAX_TIMEOUT'] = 60
    
    # Set maximum script timeout
    try:
        app.config['SCRIPT_MAX_TIMEOUT'] = int(os.environ.get('SCRIPT_MAX_TIMEOUT', 60))
    except ValueError:
        logger.warning("Invalid SCRIPT_MAX_TIMEOUT value, using default of 60 seconds")
        app.config['SCRIPT_MAX_TIMEOUT'] = 60
    
    # Load script configurations
    if is_enabled('ENABLE_SCRIPTS_ENDPOINT'):
        script_configs = load_script_configs()
        if script_configs:
            logger.info(f"Loaded {len(script_configs)} script configurations")
        else:
            logger.warning("No script configurations found")
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Log enabled/disabled endpoints
    enabled_endpoints = []
    if is_enabled('ENABLE_STATUS_ENDPOINT'):
        enabled_endpoints.append('/')
    if is_enabled('ENABLE_SYSTEM_ENDPOINT'):
        enabled_endpoints.append('/api/system')
    if is_enabled('ENABLE_DOCKER_ENDPOINT'):
        enabled_endpoints.append('/api/docker')
    if is_enabled('ENABLE_COMMAND_ENDPOINT'):
        enabled_endpoints.append('/api/execute')
    if is_enabled('ENABLE_SCRIPTS_ENDPOINT'):
        enabled_endpoints.append('/api/scripts')
        enabled_endpoints.append('/api/scripts/<script_name>')
    if is_enabled('ENABLE_PROCESSES_ENDPOINT'):
        enabled_endpoints.append('/api/processes')
        enabled_endpoints.append('/api/processes/<process_id>')
    
    logger.info(f"Enabled endpoints: {', '.join(enabled_endpoints)}")
    logger.info(f"Starting Flask API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)