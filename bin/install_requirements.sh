#!/usr/bin/env bash

DINO_CONDA_ENV=$1

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
        echo "error: no virtual environment found in env/ and no conda executable found"
        exit 1
    fi
    if ! source activate ${DINO_CONDA_ENV}; then
        echo "error: could not activate conda environment $DINO_CONDA_ENV"
        exit 1
    fi
fi

echo "installing requirements... "
if ! pip install -r requirements.txt; then
    echo "error: could not install requirements"
    exit 1
fi

echo "installing current dino version... "
if ! pip install --no-cache --no-deps --upgrade .; then
    echo "error: could not install current dino version"
    exit 1
fi
