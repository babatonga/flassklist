#!/bin/bash

LOCAL_PASSLISTDATA="${COMB_PASSLIST_DATA:-/passlistdata}"
RAMDISK_DIR="${COMB_RAMDISK_DIR:-/ramdiskdata}"
RAM_PASSLISTDATA="$RAMDISK_DIR/data"

if [ -d "$RAM_PASSLISTDATA" ]; then
    echo "[INFO] Using RAM disk data directory: $RAM_PASSLISTDATA"
    PASSLISTDATA="$RAM_PASSLISTDATA"
elif [ -d "$RAMDISK_DIR" ]; then
    echo "[INFO] Creating RAM disk data directory: $RAM_PASSLISTDATA"
    cp -r "$LOCAL_PASSLISTDATA" "$RAM_PASSLISTDATA"
    echo "[INFO] Using RAM disk data directory: $RAM_PASSLISTDATA"
    PASSLISTDATA="$RAM_PASSLISTDATA"
else
    echo "[WARNING] RAM disk not found: $RAMDISK_DIR"
    echo "[INFO] Using local data directory: $LOCAL_PASSLISTDATA"
    PASSLISTDATA="$LOCAL_PASSLISTDATA"
fi

exec gunicorn -w 4 -b 0.0.0.0:8080 app:app
