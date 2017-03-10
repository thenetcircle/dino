#!/usr/bin/env bash

LOG_DIR=/var/log/dino

if [ -z $DINO_HOME ]; then
    DINO_HOME=/home/dino/dino/
fi

if [ $# -ne 3 ]; then
    echo "usage: $0 <environment> <port> <app/rest/web>"
    exit 1
fi

re='^[0-9]+$'
if ! [[ $2 =~ $re ]] ; then
   echo "error: Port a number"
   exit 1
fi

if [[ $2 -lt 1 || $2 -gt 65536 ]]; then
    echo "error: port '$2' not in range 1-65536"
    exit 1
fi

if ! [[ "$3" =~ ^(app|rest|web)$ ]]; then
    echo "error: invalid module '$3', not one of app/rest/web"
    exit 1
fi

if [ ! -d $DINO_HOME ]; then
    echo "error: home directory '$DINO_HOME' not found"
    exit 1
fi

if [ ! -f env/bin/activate ]; then
    echo "error: no virtual environment found in $DINO_HOME/env"
    exit 1
fi

if [ ! -d /var/log/dino/ ]; then
    if ! [ mkdir -p ${LOG_DIR} ]; then
        echo "error: could not create missing log directory '$LOG_DIR'"
        exit 1
    fi
fi

if ! cd ${DINO_HOME}; then
    echo "error: could not change to home directory '$DINO_HOME'"
    exit 1
fi

if ! source env/bin/activate; then
    echo "error: could not source virtual env"
    exit 1
fi

DINO_ENVIRONMENT=$1 DINO_DEBUG=0 gunicorn \
    --worker-class eventlet \
    -w 1 \
    --threads 1 \
    --worker-connections 1000 \
    -b 0.0.0.0:$2 \
    $3:app 2>&1 >> ${LOG_DIR}/dino-$3-$1.log
