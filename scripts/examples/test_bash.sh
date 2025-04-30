#!/bin/bash

# Read JSON input from stdin
input_json=$(cat)

# Attempt to parse the test_message field using jq.
# -e exits with error if key not found or input is invalid JSON.
# -r outputs raw string without quotes.
# Errors are redirected to /dev/null to keep the output clean.
test_message=$(echo "$input_json" | jq -e -r '.test_message' 2>/dev/null)

# Check the exit status of jq
if [ $? -eq 0 ]; then
  # jq succeeded, use the extracted message
  output_message="$test_message"
else
  # jq failed (not installed, invalid JSON, or key missing)
  output_message="Default message: Could not extract 'test_message' from input."
fi

# Output the result as JSON
# Use printf for safer JSON string escaping
printf '{"message": "%s"}\n' "$output_message"