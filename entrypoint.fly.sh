
#!/bin/bash

if [ "$1" = "dashboard" ]; then
  echo "Starting Dashboard..."
  cd /app/placer-dashboard
  deno task start

elif [ "$1" = "placer" ]; then
  echo "Starting Placer Service..."
  # Create logs directory if it doesn't exist
  mkdir -p /app/placer-service/data/logs
  
  cd /app/placer-service
  poetry run python3 main.py

else
  echo "Unknown process group: $1"
  exit 1
fi