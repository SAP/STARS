#!/bin/sh

# Generate runtime configuration from environment variables
# This script runs at container startup to create config.json from environment variables

# Validate required environment variables
required_vars="BACKEND_URL BACKEND_WS_URL API_URL"
for var in $required_vars; do
    if [ -z "$(eval echo \$$var)" ]; then
        echo "Warning: $var is not set, using default value"
    fi
done

# Set default values if environment variables are not provided
BACKEND_URL=${BACKEND_URL:-"http://localhost:8080"}
BACKEND_WS_URL=${BACKEND_WS_URL:-"ws://localhost:8080/agent"}
API_URL=${API_URL:-"http://localhost:8080"}

# Generate the config.json file (directory already created with proper permissions)
cat > /usr/share/nginx/html/assets/configs/config.json << EOF
{
  "backend_url": "${BACKEND_URL}/process",
  "backend_url_ws": "${BACKEND_WS_URL}",
  "api_url": "${API_URL}"
}
EOF

echo "Generated runtime configuration:"
cat /usr/share/nginx/html/assets/configs/config.json

echo "Starting nginx..."
exec "$@"
