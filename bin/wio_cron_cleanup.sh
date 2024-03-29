#!/usr/bin/env bash

DINO_HOME=$1
DINO_ENV=$2
DINO_CONDA_ENV=$3

if [[ -z "$DINO_HOME" ]]; then
    echo "error: set DINO_HOME first"
    exit 1
fi
if [[ -z "$DINO_CONDA_ENV" ]]; then
    DINO_CONDA_ENV="env"
fi

if [ -f env/bin/activate ]; then
    if [ -z "$VIRTUAL_ENV" ]; then
        if ! source env/bin/activate; then
            echo "error: could not source virtual env"
            exit 1
        fi
    fi
else
    if ! which conda >/dev/null; then
        echo "error: no virtual environment found in $DINO_HOME/env and no conda executable found"
        exit 1
    fi
    if ! source activate ${DINO_CONDA_ENV}; then
        echo "error: could not activate conda environment $DINO_CONDA_ENV"
        exit 1
    fi
fi

echo "clearing expired bans and hanging acls... "
if ! python bin/clear_db_acls_bans_table.py ${DINO_ENV} ${DINO_HOME}; then
    echo "error: could not clear acls/bans tables"
    exit 1
fi

echo "clearing old room roles and rooms... "
if ! python bin/clear_db_rooms_table.py ${DINO_ENV} ${DINO_HOME}; then
    echo "error: could not clear rooms/roles tables"
    exit 1
fi
