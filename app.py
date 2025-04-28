import os
import logging
import json
from flask import Flask, jsonify, request
from flask_restful import Api
from flask_cors import CORS  # Import CORS
from dotenv import load_dotenv
from datetime import datetime
from app.routes import get_api_resources

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Enable CORS with more explicit configuration
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*", "methods": ["GET", "POST", "OPTIONS"]}})

# Instantiate API
api = Api(app)

# Get API resources
api_resources = get_api_resources()

# Register API endpoints
for resource in api_resources:
    if resource['enabled']:
        logger.info(f"Enabling endpoint: {resource['endpoint']}")
        api.add_resource(resource['resource'], resource['endpoint'])

# Add a CORS preflight route for all endpoints
@app.route('/', methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path=''):
    return '', 200

if __name__ == '__main__':
    # Log enabled endpoints
    enabled_endpoints = [r['endpoint'] for r in api_resources if r['enabled']]
    logger.info(f"Enabled endpoints: {', '.join(enabled_endpoints)}")
    
    # Start the server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info(f"Starting Flask API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)