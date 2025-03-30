#!/bin/bash

#Set the environment variables
export COMB_PASSLIST_DATA=${COMB_PASSLIST_DATA:-/passlistdata}
export COMB_REDIS_URL=${COMB_REDIS_URL:-redis://localhost:6379}

if [ -d "$COMB_PASSLIST_DATA" ]; then
    echo "[INFO] Using data directory: $COMB_PASSLIST_DATA"
else
    echo "[ERROR] Data directory not found: $COMB_PASSLIST_DATA"
    exit 1
fi

cd app/
gunicorn -w 4 -b 127.0.0.1:8080 app:app