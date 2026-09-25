#!/bin/sh
set -eu
cd /app
mkdir -p data
chown -R app:app data
exec gosu app python main.py
