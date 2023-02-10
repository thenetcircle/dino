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

echo "clearing online cache... "
if ! /root/miniconda3/bin/conda run -n ${DINO_CONDA_ENV} python bin/clear_redis_cache.py ${DINO_ENV} ${DINO_HOME}; then
    echo "error: could not clear redis cache"
    exit 1
fi

echo "clearing online db tables... "
if ! /root/miniconda3/bin/conda run -n ${DINO_CONDA_ENV} python bin/clear_db_online_table.py ${DINO_ENV} ${DINO_HOME}; then
    echo "error: could not clear online tables"
    exit 1
fi

echo "clearing sessions db tables... "
if ! /root/miniconda3/bin/conda run -n ${DINO_CONDA_ENV} python bin/clear_db_sessions_table.py ${DINO_ENV} ${DINO_HOME}; then
    echo "error: could not clear sessions tables"
    exit 1
fi

echo "clearing expired bans and hanging acls... "
if ! /root/miniconda3/bin/conda run -n ${DINO_CONDA_ENV} python bin/clear_db_acls_bans_table.py ${DINO_ENV} ${DINO_HOME}; then
    echo "error: could not clear acls/bans tables"
    exit 1
fi

echo "warming up cache... "
if ! DINO_ENVIRONMENT=${DINO_ENV} DINO_HOME=${DINO_HOME} /root/miniconda3/bin/conda run -n ${DINO_CONDA_ENV} python bin/warm_up_cache.py; then
    echo "error: could not warm up cache"
    exit 1
fi
