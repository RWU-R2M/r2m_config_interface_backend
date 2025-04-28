# System Monitoring REST API

A Flask-based REST API server for monitoring system resources, Docker containers, and executing system commands. This server provides endpoints to retrieve system information and status about the host machine and Docker containers.

## Features

- System resource monitoring (CPU, memory, disk, network)
- Docker container monitoring
- Command execution endpoint for running system commands
- Custom script execution via API endpoints with process management
- Automatic cleanup of finished asynchronous processes
- JSON response format
- Error handling and logging
- Configurable API endpoints via environment variables
- Command whitelisting for enhanced security

## Requirements

- Python 3.6+
- Flask and Flask-RESTful
- psutil for system monitoring
- Docker (if using Docker container monitoring features)
- PyYAML (for script configuration files)

## Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   Create a `.env` file in the project root with your desired configuration:
   ```properties
   # Server Configuration
   PORT=5000
   FLASK_DEBUG=True

   # API Route Configurations (true/false)
   ENABLE_STATUS_ENDPOINT=true
   ENABLE_SYSTEM_ENDPOINT=true
   ENABLE_DOCKER_ENDPOINT=true
   ENABLE_COMMAND_ENDPOINT=true
   ENABLE_SCRIPTS_ENDPOINT=true
   ENABLE_PROCESSES_ENDPOINT=true

   # Security Settings
   COMMAND_WHITELIST=ls,df,ps,free,top,docker,cat,echo,hostname
   COMMAND_MAX_TIMEOUT=60
   SCRIPT_MAX_TIMEOUT=60
   ```

3. Run the server:
   ```bash
   python app.py
   ```

## Configuration

The server can be configured using environment variables in the `.env` file. You can:

- Enable/disable specific API endpoints
- Configure security settings for the command execution endpoint
- Set server port and debug mode

### API Endpoint Configuration

Each API endpoint can be independently enabled or disabled:

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `ENABLE_STATUS_ENDPOINT` | true | Enable/disable the base status endpoint (/) |
| `ENABLE_SYSTEM_ENDPOINT` | true | Enable/disable the system information endpoint (/api/system) |
| `ENABLE_DOCKER_ENDPOINT` | true | Enable/disable the Docker containers endpoint (/api/docker) |
| `ENABLE_COMMAND_ENDPOINT` | true | Enable/disable the command execution endpoint (/api/execute) |
| `ENABLE_SCRIPTS_ENDPOINT` | true | Enable/disable the custom scripts endpoints (/api/scripts) |
| `ENABLE_PROCESSES_ENDPOINT` | true | Enable/disable the process management endpoints (/api/processes) |

Set any of these variables to `false` to disable the corresponding endpoint.

### Security Settings

For the command execution endpoint (`/api/execute`), additional security settings are available:

| Environment Variable | Description |
|----------------------|-------------|
| `COMMAND_WHITELIST` | Comma-separated list of allowed commands. Only base commands listed here can be executed. |
| `COMMAND_MAX_TIMEOUT` | Maximum execution time in seconds for any command (default: 60) |
| `SCRIPT_MAX_TIMEOUT` | Maximum execution time in seconds for custom scripts (default: 60) |

If `COMMAND_WHITELIST` is empty, all commands will be allowed (not recommended for production).

Example configuration with restricted commands:
```properties
COMMAND_WHITELIST=ls,df,ps,docker
COMMAND_MAX_TIMEOUT=30
SCRIPT_MAX_TIMEOUT=30
```

### Server Configuration

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `PORT` | 5000 | The port the server will listen on |
| `FLASK_DEBUG` | False | Enable/disable Flask debug mode |

## Custom Scripts

The server supports executing custom scripts through the API. This allows you to extend the functionality without modifying the core code.

### Process Management

Asynchronous scripts are executed in the background and their processes are automatically managed by the server:

- Each process is tracked with a unique process ID
- A background thread monitors running processes and marks them as completed when they finish
- Completed processes are kept in memory for an hour for status checking
- Old completed processes are automatically removed to free up memory

### Creating Custom Scripts

1. Place your script files in the `scripts/` directory.
2. Create a configuration file for each script in the `config/scripts/` directory.

### Script Configuration Files

Script configuration files can be in YAML or JSON format and should include the following fields:

```yaml
name: "example-script"               # Unique name for the script
description: "An example script"     # Human-readable description
script_path: "example.py"            # Path to the script file (relative to the scripts/ directory)
endpoint: "example"                  # Custom endpoint name (will be accessible at /api/scripts/example-script)
accepts_input: true                  # Whether the script accepts input parameters (true/false)
input_method: "json"                 # How input is passed to the script: "json" (via stdin) or "env" (as environment variables)
async: false                         # Whether the script runs asynchronously (true) or synchronously (false)
expected_output: {                   # Description of expected output structure (for documentation)
  "status": "string",
  "value": "number"
}
input_schema: {                      # Description of expected input structure (for documentation)
  "param1": "string",
  "param2": "number"
}
```

#### Script Types and Execution

- **Python scripts** (`.py`) will be executed with `python script.py`
- **Shell scripts** (`.sh`, `.bash`) will be executed with `bash script.sh`
- Other script types will be executed directly

#### Input and Output Handling

- For scripts that accept input (`accepts_input: true`):
  - If `input_method: "json"`, input is passed as JSON via stdin
  - If `input_method: "env"`, input is passed as environment variables

- For synchronous scripts (`async: false`):
  - Output must be valid JSON printed to stdout
  - The API will parse this JSON and return it

- For asynchronous scripts (`async: true`):
  - The API immediately returns a success response with a process ID
  - The process runs in the background
  - No output parsing is performed
  - Process status can be checked via the `/api/processes/<process_id>` endpoint
  - The process is automatically cleaned up after completion

### Example Script Configuration

```yaml
name: "system-status"
description: "Get detailed system status information"
script_path: "system_status.py"
endpoint: "status"
accepts_input: false
async: false
expected_output: {
  "status": "string",
  "cpu_temp": "number",
  "uptime": "string"
}
```

## API Endpoints

### Base URL
By default, the API is available at `http://localhost:5000`

### API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server status check |
| `/api/system` | GET | Get detailed system statistics |
| `/api/docker` | GET | Get information about Docker containers |
| `/api/execute` | POST | Execute system commands |
| `/api/scripts` | GET | List available custom scripts |
| `/api/scripts/<script_name>` | POST | Execute a custom script |
| `/api/processes` | GET | List all tracked script processes |
| `/api/processes/<process_id>` | GET | Get status of a specific process |

### Endpoint Details

#### GET /
Returns basic server status information.

**Response Example:**
```json
{
  "status": "running",
  "server_time": "2025-04-28 12:34:56",
  "message": "REST API server is running"
}
```

#### GET /api/system
Returns detailed system statistics including CPU, memory, disk and network information.

**Response Example:**
```json
{
  "cpu": {
    "total_percent": 12.5,
    "per_core": [10.2, 15.3, 12.0, 12.5],
    "cores": 4,
    "physical_cores": 2
  },
  "memory": {
    "total": 16777216000,
    "available": 8388608000,
    "used": 8388608000,
    "percent": 50.0
  },
  "disk": {
    "total": 1099511627776,
    "used": 549755813888,
    "free": 549755813888,
    "percent": 50.0
  },
  "network": {
    "eth0": {
      "bytes_sent": 1024000,
      "bytes_recv": 2048000,
      "packets_sent": 1000,
      "packets_recv": 2000
    }
  }
}
```

#### GET /api/docker
Returns information about Docker containers.

**Response Example:**
```json
{
  "containers": [
    {
      "ID": "123abc456def",
      "Names": "web-server",
      "Image": "nginx:latest",
      "Command": "nginx -g 'daemon off;'",
      "Created": "2023-04-01 00:00:00",
      "Status": "Up 10 days",
      "Ports": "80/tcp, 443/tcp",
      "Size": "128MB"
    }
  ]
}
```

#### POST /api/execute
Executes a system command and returns the result.

**Request:**
```json
{
  "command": "ls -la",
  "timeout": 30
}
```

**Response Example:**
```json
{
  "command": "ls -la",
  "returncode": 0,
  "stdout": "total 32\ndrwxr-xr-x 4 user user 4096 Apr 27 12:00 .\n...",
  "stderr": "",
  "success": true
}
```

#### GET /api/scripts
Returns a list of available custom scripts and their configurations.

**Response Example:**
```json
{
  "scripts": [
    {
      "name": "system-status",
      "description": "Get detailed system status information",
      "endpoint": "status",
      "accepts_input": false,
      "async": false,
      "expected_output": {
        "status": "string",
        "cpu_temp": "number",
        "uptime": "string"
      }
    },
    {
      "name": "long-task",
      "description": "Start a system service",
      "endpoint": "task",
      "accepts_input": true,
      "async": true,
      "input_schema": {
        "task_name": "string",
        "duration": "number"
      }
    }
  ]
}
```

#### POST /api/scripts/<script_name>
Executes a custom script with optional input parameters and returns the result.

**Request Example (for a script that accepts input):**
```json
{
  "param1": "value1",
  "param2": 42
}
```

**Response Example (for a synchronous script):**
```json
{
  "script": "example-script",
  "returncode": 0,
  "output": {
    "status": "success",
    "value": 42
  },
  "stderr": "",
  "success": true
}
```

**Response Example (for an asynchronous script):**
```json
{
  "script": "long-task",
  "process_id": 12345,
  "async": true,
  "message": "Script 'long-task' started asynchronously",
  "success": true
}
```

#### GET /api/processes
Returns a list of all tracked processes, both running and completed.

**Response Example:**
```json
{
  "processes": [
    {
      "script": "long-task",
      "process_id": 12345,
      "running": false,
      "start_time": 1650000000.123,
      "duration": 15.5,
      "completed": true,
      "returncode": 0,
      "end_time": 1650000015.623,
      "exit_status": "success"
    },
    {
      "script": "another-task",
      "process_id": 12346,
      "running": true,
      "start_time": 1650000030.456,
      "duration": 10.2
    }
  ]
}
```

#### GET /api/processes/<process_id>
Returns the status of a specific process.

**Response Example (for a completed process):**
```json
{
  "script": "long-task",
  "process_id": 12345,
  "running": false,
  "start_time": 1650000000.123,
  "duration": 15.5,
  "completed": true,
  "returncode": 0,
  "end_time": 1650000015.623,
  "exit_status": "success",
  "success": true
}
```

**Response Example (for a running process):**
```json
{
  "script": "long-task",
  "process_id": 12345,
  "running": true,
  "start_time": 1650000000.123,
  "duration": 5.2,
  "success": true
}
```

## Security Considerations

⚠️ **Warning**: The command execution and script execution endpoints can pose significant security risks if not properly restricted. For enhanced security:

- Use the `COMMAND_WHITELIST` setting to restrict allowed commands
- Disable the command execution endpoint in production if not needed by setting `ENABLE_COMMAND_ENDPOINT=false`
- Verify all custom scripts before deployment
- Use proper authentication and authorization
- Consider running the server in a restricted environment
- Avoid exposing the server directly to the internet

## Project Structure

```
.
├── app.py              # Main application entry point
├── requirements.txt    # Python dependencies
├── .env                # Environment configuration
├── API_DOCUMENTATION.md # Detailed API documentation
├── app/
│   ├── __init__.py     # Package initialization
│   ├── routes.py       # API route definitions
│   └── utils.py        # Utility functions for system monitoring
├── scripts/
│   ├── README.md       # Documentation for script development
│   └── examples/       # Example script implementations
│       ├── example_long_task.py
│       └── example_system_status.py
├── config/
│   └── scripts/        # Script configuration files
│       ├── long_task.yaml
│       └── system_status.yaml
├── test/
│   ├── test_api_simple.py     # Python test script
│   └── test_process_management.py  # Process management tests
└── README.md           # This documentation
```

## Development

### Adding new endpoints

1. Define a new Resource class in `app/routes.py`
2. Add it to the `api_resources` list
3. Implement the necessary utility functions in `app/utils.py` 
4. Add a configuration variable to .env if you want the endpoint to be configurable

### Adding new custom scripts

1. Create your script file in the `scripts/` directory
2. Create a configuration file in `config/scripts/` directory (YAML or JSON)
3. Make sure your script follows the input/output conventions:
   - Accept input via stdin if `input_method: "json"`
   - Accept input via environment variables if `input_method: "env"`
   - Output valid JSON to stdout for synchronous scripts

### Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | 5000 |
| `FLASK_DEBUG` | Enable debug mode | False |
| `ENABLE_STATUS_ENDPOINT` | Enable base status endpoint | true |
| `ENABLE_SYSTEM_ENDPOINT` | Enable system info endpoint | true |
| `ENABLE_DOCKER_ENDPOINT` | Enable Docker containers endpoint | true |
| `ENABLE_COMMAND_ENDPOINT` | Enable command execution endpoint | true |
| `ENABLE_SCRIPTS_ENDPOINT` | Enable custom scripts endpoints | true |
| `ENABLE_PROCESSES_ENDPOINT` | Enable process management endpoints | true |
| `COMMAND_WHITELIST` | Allowed commands for execution | (none) |
| `COMMAND_MAX_TIMEOUT` | Maximum command timeout in seconds | 60 |
| `SCRIPT_MAX_TIMEOUT` | Maximum script timeout in seconds | 60 |

## Further Documentation

For detailed API specifications, request/response formats, and integration examples, see the [API Documentation](API_DOCUMENTATION.md).

## License

[MIT License](LICENSE)