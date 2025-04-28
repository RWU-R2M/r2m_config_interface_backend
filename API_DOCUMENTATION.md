# System Monitoring API Documentation

This document provides detailed specifications for the REST API endpoints of the System Monitoring service. This documentation is designed for developers and AI agents integrating with these APIs.

## API Base URL

```
http://localhost:5000
```

## Authentication

Currently, the API does not implement authentication. For production use, consider adding appropriate authentication mechanisms.

## Configuration (.env File)

The API server can be configured using environment variables in a `.env` file. This allows you to enable or disable specific endpoints for security purposes and configure other security settings.

### Available Configuration Options

```properties
# Server Configuration
PORT=5000                      # Port the server listens on
FLASK_DEBUG=True               # Enable/disable debug mode

# API Route Configurations (true/false)
ENABLE_STATUS_ENDPOINT=true    # Base status endpoint (/)
ENABLE_SYSTEM_ENDPOINT=true    # System info endpoint (/api/system)
ENABLE_DOCKER_ENDPOINT=true    # Docker containers endpoint (/api/docker)
ENABLE_COMMAND_ENDPOINT=true   # Command execution endpoint (/api/execute)
ENABLE_SCRIPTS_ENDPOINT=true   # Custom scripts endpoints (/api/scripts)
ENABLE_PROCESSES_ENDPOINT=true # Process management endpoints (/api/processes)

# Security Settings
# Comma-separated list of allowed commands (empty = no restrictions)
COMMAND_WHITELIST=ls,df,ps,free,top,docker,cat,echo,hostname

# Maximum timeout for command execution in seconds
COMMAND_MAX_TIMEOUT=60

# Maximum timeout for script execution in seconds
SCRIPT_MAX_TIMEOUT=60
```

### Enabling/Disabling Endpoints

Set the corresponding environment variable to `true` to enable an endpoint or `false` to disable it. When an endpoint is disabled, requests to that endpoint will receive a 404 Not Found response.

### Command Whitelist

The `COMMAND_WHITELIST` setting controls which commands can be executed through the `/api/execute` endpoint. Only the base command (first word) is checked against the whitelist. For example, if `ls` is in the whitelist, then commands like `ls -la` or `ls /home` will be allowed.

If the whitelist is empty, all commands will be allowed (not recommended for production).

## Response Format

All API responses are in JSON format. Successful requests typically return HTTP status code 200 with a JSON response body. Failed requests return appropriate HTTP error codes (4xx for client errors, 5xx for server errors) with a JSON body containing error information.

Standard error response format:
```json
{
  "error": "Error message describing what went wrong"
}
```

## Rate Limiting

No rate limiting is currently implemented.

---

## Endpoint: Server Status

Provides basic information about the server status.

**Configurable**: This endpoint can be enabled/disabled using the `ENABLE_STATUS_ENDPOINT` environment variable.

### Request

```
GET /
```

### Response

#### Success Response (200 OK)

```json
{
  "status": "running",
  "server_time": "2025-04-28 12:34:56",
  "message": "REST API server is running"
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| status | string | Current status of the server, typically "running" |
| server_time | string | Current server time in "YYYY-MM-DD HH:MM:SS" format |
| message | string | Human-readable status message |

### Example

```bash
curl -X GET http://localhost:5000/
```

---

## Endpoint: System Statistics

Retrieves detailed system resource statistics including CPU, memory, disk usage, and network information.

**Configurable**: This endpoint can be enabled/disabled using the `ENABLE_SYSTEM_ENDPOINT` environment variable.

### Request

```
GET /api/system
```

### Response

#### Success Response (200 OK)

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
    },
    "wlan0": {
      "bytes_sent": 512000,
      "bytes_recv": 1024000,
      "packets_sent": 500,
      "packets_recv": 1000
    }
  }
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| cpu.total_percent | float | Overall CPU usage percentage (0-100) |
| cpu.per_core | array of float | CPU usage percentage for each core |
| cpu.cores | integer | Number of logical CPU cores |
| cpu.physical_cores | integer | Number of physical CPU cores |
| memory.total | integer | Total physical memory in bytes |
| memory.available | integer | Available memory in bytes |
| memory.used | integer | Used memory in bytes |
| memory.percent | float | Memory usage percentage (0-100) |
| disk.total | integer | Total disk space in bytes |
| disk.used | integer | Used disk space in bytes |
| disk.free | integer | Free disk space in bytes |
| disk.percent | float | Disk usage percentage (0-100) |
| network | object | Object containing network interface statistics |
| network.{interface} | object | Statistics for a specific network interface |
| network.{interface}.bytes_sent | integer | Total bytes sent by the interface |
| network.{interface}.bytes_recv | integer | Total bytes received by the interface |
| network.{interface}.packets_sent | integer | Total packets sent by the interface |
| network.{interface}.packets_recv | integer | Total packets received by the interface |

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Error message describing the issue"
}
```

### Example

```bash
curl -X GET http://localhost:5000/api/system
```

### Notes

- All memory and disk sizes are reported in bytes
- CPU percentages range from 0 to 100 (not 0 to 1)
- Network interfaces will vary by system

---

## Endpoint: Docker Containers Information

Retrieves information about Docker containers running on the system.

**Configurable**: This endpoint can be enabled/disabled using the `ENABLE_DOCKER_ENDPOINT` environment variable.

### Request

```
GET /api/docker
```

### Response

#### Success Response (200 OK)

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
      "Size": "128MB",
      "Networks": "bridge",
      "State": "running"
    },
    {
      "ID": "789xyz012uvw",
      "Names": "database",
      "Image": "postgres:13",
      "Command": "postgres",
      "Created": "2023-04-01 00:00:00",
      "Status": "Up 5 days",
      "Ports": "5432/tcp",
      "Size": "256MB",
      "Networks": "bridge",
      "State": "running"
    }
  ]
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| containers | array | Array of container objects |
| containers[].ID | string | Docker container ID |
| containers[].Names | string | Container name |
| containers[].Image | string | Container image name and tag |
| containers[].Command | string | Command running in the container |
| containers[].Created | string | Creation timestamp |
| containers[].Status | string | Container status (e.g., "Up 10 days") |
| containers[].Ports | string | Exposed ports |
| containers[].Size | string | Container size information |
| containers[].Networks | string | Networks the container is connected to |
| containers[].State | string | Container state (running, exited, etc.) |
| containers[].Labels | string | Container labels (optional) |
| containers[].Mounts | string | Volume mounts (optional) |

Note: The exact fields may vary depending on the output format of the Docker CLI.

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Error message describing the issue"
}
```

### Example

```bash
curl -X GET http://localhost:5000/api/docker
```

### Docker Client Requirement

This endpoint requires the Docker daemon to be running on the host system and accessible to the API server user.

---

## Endpoint: Command Execution

Executes a specified command on the server and returns the result. This endpoint accepts POST requests with a JSON body containing the command to execute.

**Configurable**: 
- This endpoint can be enabled/disabled using the `ENABLE_COMMAND_ENDPOINT` environment variable.
- Commands that can be executed are restricted by the `COMMAND_WHITELIST` setting in the `.env` file.
- The maximum allowed timeout is controlled by the `COMMAND_MAX_TIMEOUT` setting.

### Request

```
POST /api/execute
```

#### Request Body

```json
{
  "command": "ls -la /home",
  "timeout": 30
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| command | string | Yes | The command to execute on the server (must be in the whitelist) |
| timeout | integer | No | Maximum execution time in seconds (capped by COMMAND_MAX_TIMEOUT) |

### Response

#### Success Response (200 OK)

```json
{
  "command": "ls -la /home",
  "returncode": 0,
  "stdout": "total 32\ndrwxr-xr-x 4 root root 4096 Apr 27 12:00 .\ndrwxr-xr-x 24 root root 4096 Apr 27 12:00 ..\ndrwxr-xr-x 43 user user 4096 Apr 27 12:00 user\n",
  "stderr": "",
  "success": true
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| command | string | The command that was executed |
| returncode | integer | The exit code of the command (0 usually indicates success) |
| stdout | string | Standard output from the command |
| stderr | string | Standard error output from the command |
| success | boolean | Whether the command executed successfully (returncode == 0) |

#### Error Response (400 Bad Request)

```json
{
  "error": "Request must be JSON"
}
```

or

```json
{
  "error": "command parameter is required"
}
```

#### Error Response (403 Forbidden)

```json
{
  "error": "Command 'rm' is not allowed. Allowed commands: ls, df, ps, free, top, docker, cat, echo, hostname"
}
```

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Error message describing the issue"
}
```

### Example

```bash
curl -X POST http://localhost:5000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "echo Hello World", "timeout": 10}'
```

### Security Considerations

⚠️ **WARNING**: This endpoint can execute arbitrary commands on the server. In a production environment:

1. Use the `COMMAND_WHITELIST` setting to restrict which commands can be executed
2. Set `ENABLE_COMMAND_ENDPOINT=false` if command execution is not needed
3. Consider implementing authentication before enabling this endpoint
4. Run in a sandboxed environment

---

## Endpoint: List Available Scripts

Lists all available custom scripts that can be executed via the API. This provides information about the scripts' capabilities, input requirements, and expected outputs.

**Configurable**: This endpoint can be enabled/disabled using the `ENABLE_SCRIPTS_ENDPOINT` environment variable.

### Request

```
GET /api/scripts
```

### Response

#### Success Response (200 OK)

```json
{
  "scripts": [
    {
      "name": "example-system-status",
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

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| scripts | array | Array of script configuration objects |
| scripts[].name | string | Unique name of the script |
| scripts[].description | string | Human-readable description of what the script does |
| scripts[].endpoint | string | Custom endpoint path for the script |
| scripts[].accepts_input | boolean | Whether the script accepts input parameters |
| scripts[].async | boolean | Whether the script runs asynchronously |
| scripts[].expected_output | object | (Optional) Description of the script's expected output format |
| scripts[].input_schema | object | (Optional) Description of the script's expected input format |

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Error message describing the issue"
}
```

### Example

```bash
curl -X GET http://localhost:5000/api/scripts
```

---

## Endpoint: Execute Custom Script

Executes a custom script with optional input parameters and returns the result. This endpoint is used to run user-defined scripts that have been configured on the server.

**Configurable**: This endpoint can be enabled/disabled using the `ENABLE_SCRIPTS_ENDPOINT` environment variable.

### Request

```
POST /api/scripts/{script_name}
```

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| script_name | string | Yes | The name of the script to execute as defined in its configuration file |

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| timeout | integer | No | Maximum execution time in seconds (capped by SCRIPT_MAX_TIMEOUT) |

#### Request Body

```json
{
  "param1": "value1",
  "param2": 42
}
```

The request body is optional and only required if the script is configured to accept input (`accepts_input: true` in the script configuration). The format of the input data depends on the specific script's requirements as defined in its `input_schema`.

### Response

#### Success Response for Synchronous Scripts (200 OK)

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

#### Fields (Synchronous Scripts)

| Field | Type | Description |
|-------|------|-------------|
| script | string | The name of the script that was executed |
| returncode | integer | The exit code of the script (0 usually indicates success) |
| output | object | The parsed JSON output from the script |
| stderr | string | Standard error output from the script |
| success | boolean | Whether the script executed successfully (returncode == 0) |

#### Success Response for Asynchronous Scripts (200 OK)

```json
{
  "script": "long-task",
  "process_id": 12345,
  "async": true,
  "message": "Script 'long-task' started asynchronously",
  "success": true
}
```

#### Fields (Asynchronous Scripts)

| Field | Type | Description |
|-------|------|-------------|
| script | string | The name of the script that was executed |
| process_id | integer | The process ID of the running script |
| async | boolean | Always true for asynchronous scripts |
| message | string | Human-readable status message |
| success | boolean | Whether the script was started successfully |

#### Error Response (400 Bad Request)

```json
{
  "error": "Request body must be JSON when providing input to script"
}
```

or

```json
{
  "error": "Script output is not valid JSON",
  "script": "example-script",
  "raw_output": "This is not valid JSON",
  "success": false
}
```

#### Error Response (404 Not Found)

```json
{
  "error": "Script 'non-existent-script' not found"
}
```

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Script execution failed: Permission denied",
  "script": "example-script",
  "success": false
}
```

### Examples

#### Execute a script without input parameters:

```bash
curl -X POST http://localhost:5000/api/scripts/system-status
```

#### Execute a script with input parameters:

```bash
curl -X POST http://localhost:5000/api/scripts/long-task \
  -H "Content-Type: application/json" \
  -d '{"task_name": "data-analysis", "duration": 60}'
```

#### Execute a script with a custom timeout:

```bash
curl -X POST "http://localhost:5000/api/scripts/long-running-task?timeout=120"
```

---

## Endpoint: List Processes

Lists all tracked script processes, both running and completed. This endpoint provides a way to monitor asynchronous scripts that were started via the `/api/scripts/{script_name}` endpoint.

**Configurable**: This endpoint can be enabled/disabled using the `ENABLE_PROCESSES_ENDPOINT` environment variable.

### Request

```
GET /api/processes
```

### Response

#### Success Response (200 OK)

```json
{
  "processes": [
    {
      "script": "long-task",
      "process_id": 12345,
      "running": false,
      "start_time": 1714485123.456,
      "duration": 15.5,
      "completed": true,
      "returncode": 0,
      "end_time": 1714485138.956,
      "exit_status": "success"
    },
    {
      "script": "another-task",
      "process_id": 12346,
      "running": true,
      "start_time": 1714485200.789,
      "duration": 10.2
    }
  ]
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| processes | array | Array of process status objects |
| processes[].script | string | The name of the script associated with this process |
| processes[].process_id | integer | The unique process ID |
| processes[].running | boolean | Whether the process is still running |
| processes[].start_time | number | Unix timestamp when the process started |
| processes[].duration | number | Duration in seconds the process has been/was running |
| processes[].completed | boolean | (Only present for completed processes) Whether the process has completed |
| processes[].returncode | integer | (Only present for completed processes) The exit code of the process |
| processes[].end_time | number | (Only present for completed processes) Unix timestamp when the process ended |
| processes[].exit_status | string | (Only present for completed processes) "success" if returncode is 0, "error" otherwise |

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Error message describing the issue"
}
```

### Example

```bash
curl -X GET http://localhost:5000/api/processes
```

### Notes

- The server keeps track of completed processes for one hour, after which they are automatically removed
- For long-running processes, the duration is calculated as the current time minus the start time

---

## Endpoint: Get Process Status

Gets the status of a specific process by its ID. This endpoint provides detailed information about a script process, whether it's still running or has completed.

**Configurable**: This endpoint can be enabled/disabled using the `ENABLE_PROCESSES_ENDPOINT` environment variable.

### Request

```
GET /api/processes/{process_id}
```

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| process_id | integer | Yes | The ID of the process to get status for |

### Response

#### Success Response for Running Process (200 OK)

```json
{
  "script": "long-task",
  "process_id": 12345,
  "running": true,
  "start_time": 1714485123.456,
  "duration": 5.2,
  "success": true
}
```

#### Success Response for Completed Process (200 OK)

```json
{
  "script": "long-task",
  "process_id": 12345,
  "running": false,
  "start_time": 1714485123.456,
  "duration": 15.5,
  "completed": true,
  "returncode": 0,
  "end_time": 1714485138.956,
  "exit_status": "success",
  "success": true
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| script | string | The name of the script associated with this process |
| process_id | integer | The unique process ID |
| running | boolean | Whether the process is still running |
| start_time | number | Unix timestamp when the process started |
| duration | number | Duration in seconds the process has been/was running |
| completed | boolean | (Only present for completed processes) Whether the process has completed |
| returncode | integer | (Only present for completed processes) The exit code of the process |
| end_time | number | (Only present for completed processes) Unix timestamp when the process ended |
| exit_status | string | (Only present for completed processes) "success" if returncode is 0, "error" otherwise |
| success | boolean | Whether the API request was successful (not related to the process exit status) |

#### Error Response (404 Not Found)

```json
{
  "error": "Process ID 12345 not found",
  "success": false
}
```

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Error message describing the issue"
}
```

### Example

```bash
curl -X GET http://localhost:5000/api/processes/12345
```

### Notes

- The server keeps track of completed processes for one hour, after which they are automatically removed
- If you try to access a process ID that has been removed, you'll get a 404 Not Found error
- The status of a running process is updated in real-time when queried

---

## Script Configuration

Scripts are configured using YAML or JSON files in the `config/scripts/` directory. Each script must have its own configuration file that defines:

- The script name and description
- The path to the script file (relative to the `scripts/` directory)
- Whether the script accepts input parameters
- How input is passed to the script (JSON via stdin or as environment variables)
- Whether the script runs synchronously or asynchronously
- The expected output format (for documentation)

Example script configuration file (YAML):

```yaml
name: "example-script"
description: "An example script that processes data"
script_path: "example.py"
endpoint: "example"
accepts_input: true
input_method: "json"
async: false
expected_output: {
  "status": "string",
  "count": "number",
  "results": "array"
}
input_schema: {
  "filename": "string",
  "columns": "array of strings"
}
```

### Script Development Guidelines

When developing scripts for use with this API:

1. For synchronous scripts, always output valid JSON to stdout
2. Handle errors gracefully and return appropriate error information in the JSON output
3. If accepting input, be prepared to receive it either via stdin or environment variables
4. Keep scripts focused on a single task for better maintainability
5. Include appropriate validation for input parameters
6. Return meaningful error messages that can be relayed to clients

---

## Process Management

The server includes a built-in process management system for asynchronous scripts:

1. When an asynchronous script is started, it's assigned a unique process ID
2. The server maintains a registry of all running and recently completed processes
3. A background thread continuously monitors running processes to detect when they finish
4. When a process completes, its status is updated and it's kept in memory for one hour
5. After one hour, completed processes are automatically removed from memory
6. The status of any tracked process can be queried via the `/api/processes/{process_id}` endpoint
7. A list of all tracked processes can be obtained via the `/api/processes` endpoint

This design ensures that all asynchronous script processes are properly managed and cleaned up, preventing resource leaks and zombie processes.

---

## Versioning

This API is currently version 1.0.0.

## Integration Examples

### Python Client Example

```python
import requests
import time

BASE_URL = "http://localhost:5000"

def get_system_stats():
    response = requests.get(f"{BASE_URL}/api/system")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed: {response.text}")

def run_command(command, timeout=30):
    response = requests.post(
        f"{BASE_URL}/api/execute",
        json={"command": command, "timeout": timeout}
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed: {response.text}")

def list_scripts():
    response = requests.get(f"{BASE_URL}/api/scripts")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed: {response.text}")
        
def run_script(script_name, input_data=None, timeout=30):
    url = f"{BASE_URL}/api/scripts/{script_name}"
    if timeout != 30:
        url += f"?timeout={timeout}"
        
    if input_data:
        response = requests.post(url, json=input_data)
    else:
        response = requests.post(url)
        
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed: {response.text}")

def list_processes():
    response = requests.get(f"{BASE_URL}/api/processes")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed: {response.text}")

def get_process_status(process_id):
    response = requests.get(f"{BASE_URL}/api/processes/{process_id}")
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed: {response.text}")

def wait_for_process(process_id, check_interval=1, timeout=None):
    """Wait for a process to complete"""
    start_time = time.time()
    while True:
        if timeout is not None and time.time() - start_time > timeout:
            raise TimeoutError(f"Process {process_id} didn't complete within timeout")
            
        process = get_process_status(process_id)
        if not process.get("running", True):
            return process
            
        time.sleep(check_interval)

# Example usage
system_info = get_system_stats()
print(f"CPU Usage: {system_info['cpu']['total_percent']}%")
print(f"Memory Usage: {system_info['memory']['percent']}%")

# Execute a command
result = run_command("df -h")
if result["success"]:
    print(result["stdout"])
else:
    print(f"Command failed: {result['stderr']}")
    
# List available scripts
scripts = list_scripts()
print(f"Available scripts: {len(scripts['scripts'])}")
for script in scripts['scripts']:
    print(f"- {script['name']}: {script['description']}")
    
# Run an asynchronous script
result = run_script("long-task", {"task_name": "test-task", "duration": 30})
if result["success"]:
    process_id = result["process_id"]
    print(f"Started async process with ID: {process_id}")
    
    # Check process status
    status = get_process_status(process_id)
    print(f"Process is running: {status['running']}")
    
    # Wait for process to complete
    final_status = wait_for_process(process_id, timeout=60)
    print(f"Process completed with status: {final_status['exit_status']}")
else:
    print(f"Failed to start script: {result.get('error', 'Unknown error')}")
```

### JavaScript/Node.js Client Example

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:5000';

async function getSystemStats() {
  try {
    const response = await axios.get(`${BASE_URL}/api/system`);
    return response.data;
  } catch (error) {
    throw new Error(`API request failed: ${error.message}`);
  }
}

async function runCommand(command, timeout = 30) {
  try {
    const response = await axios.post(`${BASE_URL}/api/execute`, {
      command,
      timeout
    });
    return response.data;
  } catch (error) {
    throw new Error(`API request failed: ${error.message}`);
  }
}

async function listScripts() {
  try {
    const response = await axios.get(`${BASE_URL}/api/scripts`);
    return response.data;
  } catch (error) {
    throw new Error(`API request failed: ${error.message}`);
  }
}

async function runScript(scriptName, inputData = null, timeout = 30) {
  try {
    let url = `${BASE_URL}/api/scripts/${scriptName}`;
    if (timeout !== 30) {
      url += `?timeout=${timeout}`;
    }
    
    const response = await axios.post(url, inputData);
    return response.data;
  } catch (error) {
    throw new Error(`API request failed: ${error.message}`);
  }
}

async function listProcesses() {
  try {
    const response = await axios.get(`${BASE_URL}/api/processes`);
    return response.data;
  } catch (error) {
    throw new Error(`API request failed: ${error.message}`);
  }
}

async function getProcessStatus(processId) {
  try {
    const response = await axios.get(`${BASE_URL}/api/processes/${processId}`);
    return response.data;
  } catch (error) {
    throw new Error(`API request failed: ${error.message}`);
  }
}

async function waitForProcess(processId, checkInterval = 1000, timeout = null) {
  const startTime = Date.now();
  
  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      // Check timeout
      if (timeout !== null && Date.now() - startTime > timeout * 1000) {
        reject(new Error(`Process ${processId} didn't complete within timeout`));
        return;
      }
      
      try {
        const status = await getProcessStatus(processId);
        if (!status.running) {
          resolve(status);
          return;
        }
        
        // Process still running, check again after interval
        setTimeout(checkStatus, checkInterval);
      } catch (error) {
        reject(error);
      }
    };
    
    checkStatus();
  });
}

// Example usage
async function main() {
  try {
    const systemInfo = await getSystemStats();
    console.log(`CPU Usage: ${systemInfo.cpu.total_percent}%`);
    console.log(`Memory Usage: ${systemInfo.memory.percent}%`);
    
    // Execute a command
    const cmdResult = await runCommand('df -h');
    if (cmdResult.success) {
      console.log(cmdResult.stdout);
    } else {
      console.log(`Command failed: ${cmdResult.stderr}`);
    }
    
    // List available scripts
    const scripts = await listScripts();
    console.log(`Available scripts: ${scripts.scripts.length}`);
    scripts.scripts.forEach(script => {
      console.log(`- ${script.name}: ${script.description}`);
    });
    
    // Run an asynchronous script
    const scriptResult = await runScript('long-task', {
      task_name: 'test-task',
      duration: 30
    });
    
    if (scriptResult.success) {
      const processId = scriptResult.process_id;
      console.log(`Started async process with ID: ${processId}`);
      
      // Check process status
      const status = await getProcessStatus(processId);
      console.log(`Process is running: ${status.running}`);
      
      // Wait for process to complete
      console.log('Waiting for process to complete...');
      const finalStatus = await waitForProcess(processId, 1000, 60);
      console.log(`Process completed with status: ${finalStatus.exit_status}`);
    } else {
      console.log(`Failed to start script: ${scriptResult.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error(error.message);
  }
}

main();
```