#!/usr/bin/env bash

gunicorn \
        --error-logfile ~/dino-gunicorn-error.log \
        --log-file ~/dino-gunicorn.log \
        --worker-class eventlet \
        --threads 1 \
        --worker-connections 5000 \
        --workers 1 \
        --bind 0.0.0.0:$DINO_PORT \
        app:app
