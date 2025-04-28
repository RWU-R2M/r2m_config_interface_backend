# Scripts Directory

## Overview

This directory contains scripts that can be executed via the REST API. Scripts in this directory are automatically discovered and made available through the `/api/scripts` endpoint when properly configured.

## Script Categories

- **Example Scripts**: Located in the `examples/` subdirectory, these are demonstration scripts only and not intended for production use.
- **Production Scripts**: Scripts in the root of this directory should be used for actual system operations.

## Example Scripts

The following example scripts are provided for demonstration purposes:

- `examples/example_system_status.py`: Shows how to return system information synchronously
- `examples/example_long_task.py`: Demonstrates a long-running asynchronous task

These scripts show the proper format for both synchronous and asynchronous script execution through the API.

## Creating Your Own Scripts

To add your own scripts:

1. Create a new script file in this directory
2. Create a YAML configuration file in `../config/scripts/` directory
3. Ensure your script follows the input/output conventions:
   - For synchronous scripts: Output valid JSON to stdout
   - For async scripts: No specific output requirements
   - For scripts accepting input: Read from stdin or environment variables

See the example scripts as templates for implementing your own functionality.

## Script Configuration

Each script requires a configuration file in the `../config/scripts/` directory with the following structure:

```yaml
name: "script-name"              # Name used in API calls
description: "Script description" # Human-readable description
script_path: "script_file.py"    # Path relative to this directory
endpoint: "custom-endpoint"      # Custom endpoint path segment
accepts_input: true/false        # Whether the script accepts input
input_method: "json"             # How input is passed (json or env)
async: true/false                # Whether the script runs asynchronously
expected_output: {...}           # Documentation of expected output format
input_schema: {...}              # Documentation of expected input format
```

## Best Practices

1. Include comprehensive error handling in your scripts
2. For synchronous scripts, always return valid JSON
3. Validate all input parameters
4. Include detailed logging for debugging
5. Keep scripts focused on a single responsibility
