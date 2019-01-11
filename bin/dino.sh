#!/usr/bin/env bash

LOG_DIR=/var/log/dino

if [ $# -lt 3 ]; then
    echo "usage: $0 <environment> <port> <app/rest/web> [conda environment name (if used), defaults to 'env']"
    exit 1
fi

DINO_HOME=/home/dino/$1

re='^[0-9]+$'
if ! [[ $2 =~ $re ]] ; then
   echo "error: Port a number"
   exit 1
fi

if [[ $2 -lt 1 || $2 -gt 65536 ]]; then
    echo "error: port '$2' not in range 1-65536"
    exit 1
fi

if ! [[ "$3" =~ ^(app|rest|web|wio)$ ]]; then
    echo "error: invalid module '$3', not one of [app, rest, web, wio]"
    exit 1
fi

N_WORKERS="1"
if [[ "$3" = "rest" ]]; then
    N_WORKERS="4"
fi

if [ ! -d $DINO_HOME ]; then
    echo "error: home directory '$DINO_HOME' not found"
    exit 1
fi

if [[ -z "$DINO_CONDA_ENV" ]]; then
    DINO_CONDA_ENV="env"
fi
if [ $# -gt 3 ]; then
    DINO_CONDA_ENV="$4"
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

if [ -f env/bin/activate ]; then
    if [ -z "$VIRTUAL_ENV" ]; then
        if ! source env/bin/activate; then
            echo "error: could not source virtual env"
            exit 1
        fi
    fi
else
    source ~/.bashrc
    if ! which conda >/dev/null; then
        echo "error: no virtual environment found in $DINO_HOME/env and no conda executable found"
        exit 1
    fi
    if ! source activate ${DINO_CONDA_ENV}; then
        echo "error: could not activate conda environment $DINO_CONDA_ENV"
        exit 1
    fi
fi

STATSD_HOST=$(grep STATSD ${DINO_HOME}/secrets/${1}.yaml | sed "s/.*'\(.*\)'$/\1/g")
if [[ -z "$STATSD_HOST" ]]; then
    STATSD_HOST="localhost"
fi

DINO_ENVIRONMENT=$1 DINO_DEBUG=0 gunicorn \
    --worker-class eventlet \
    --timeout 60 \
    --workers ${N_WORKERS} \
    --threads 1 \
    --keep-alive 5 \
    --backlog 8192 \
    --worker-connections 10000 \
    --statsd-host ${STATSD_HOST}:8125 \
    --statsd-prefix gunicorn-dino-${1}-${3}-${2} \
    --name dino-${1}-${3}-${2} \
    --log-file ${LOG_DIR}/gunicorn-$3-$1.log \
    --error-logfile ${LOG_DIR}/error-$3-$1.log \
    -b 0.0.0.0:$2 \
    $3:app 2>&1 >> ${LOG_DIR}/dino-$3-$1.log
