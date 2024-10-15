#!/bin/bash

REGION="$1"
FLY_APP_NAME="$2"

# Remove all machines in the specified region
MACHINE_IDS=$(flyctl machines list --app "$FLY_APP_NAME" --region "$REGION" --json | jq -r '.[].id')

for MACHINE_ID in $MACHINE_IDS; do
  flyctl machines remove "$MACHINE_ID" --app "$FLY_APP_NAME" --force
done