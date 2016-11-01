#!/bin/bash
ENVIRONMENT=$1 gunicorn --worker-class gevent --threads 2 --worker-connections 50 --workers 1 app:app --bind 0.0.0.0:5200
