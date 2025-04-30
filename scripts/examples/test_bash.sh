#!/bin/bash

# Read JSON input from stdin
input_json=$(cat)

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    # Output error as JSON
    printf '{"error": "jq is not installed. Cannot parse JSON input."}'
    exit 1
fi

# Parse the JSON input using jq to get the test_message field
# Use -e to exit with error if key not found, || true to handle missing key gracefully
# Use -r to get raw string output without quotes
test_message=$(echo "$input_json" | jq -e -r '.test_message' 2>/dev/null)

# Check if jq failed to parse or find the key
if [ $? -ne 0 ]; then
  test_message="Default message: Input did not contain 'test_message' or was not valid JSON."
fi

# Output the result as JSON matching the expected_output schema
# Use printf for safer JSON string escaping
printf '{"message": "%s"}\n' "$test_message"