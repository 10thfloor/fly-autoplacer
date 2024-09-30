#!/bin/bash

REGION="$1"
FLY_APP_NAME="$2"

# Deploy a new machine to the specified region
flyctl machine run --region "$REGION" --app "$FLY_APP_NAME" --detach