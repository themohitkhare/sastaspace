#!/bin/bash
set -e

MODE="${MODE:-server}"

if [ "$MODE" = "worker" ]; then
    echo "Starting worker..."
    exec python -m sastaspace.worker
else
    echo "Starting server..."
    exec uvicorn sastaspace.server:app --host 0.0.0.0 --port 8080
fi
