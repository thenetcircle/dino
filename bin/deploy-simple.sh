#!/usr/bin/env bash

echo "starting deployment..."

if [[ -z "$DINO_ENVIRONMENT" ]]; then
    echo "error: environment not set, specify using DINO_ENVIRONMENT"
    exit 1
fi

if [[ -z "$DINO_HOME" ]]; then
    DINO_HOME=/home/dino/dino/
fi

if [[ ! -d "$DINO_HOME" ]]; then
    echo "error: home directory '$DINO_HOME' not found"
    exit 1
fi

if ! cd "$DINO_HOME"; then
    echo "error: could not chang to directory '$DINO_HOME'"
    exit 1
fi

if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! source env/bin/activate ]; then
        echo "error: could not activate virtual environment"
        exit 1
    fi
fi

echo "pulling from git... "
if ! git pull; then
    echo "error: could not pull from git"
    exit 1
fi

echo "stopping web... "
if ! systemctl stop dino-web; then
    echo "error: could not stop dino-web"
    exit 1
fi

echo "stopping rest... "
if ! systemctl stop dino-rest; then
    echo "error: could not stop dino-rest"
    exit 1
fi

echo "stopping app... "
if ! systemctl stop dino-app; then
    echo "error: could not stop dino-app"
    exit 1
fi

echo "clearing online cache... "
if ! python bin/clear_redis_cache.py; then
    echo "error: could not clear redis cache"
    exit 1
fi

echo "clearing online db tables... "
if ! python bin/clear_db_online_table.py; then
    echo "error: could not clear db tables"
    exit 1
fi

echo "starting app... "
if ! systemctl start dino-app; then
    echo "error: could not start dino-app"
    exit 1
fi

echo "starting rest... "
if ! systemctl start dino-rest; then
    echo "error: could not start dino-rest"
    exit 1
fi


echo "starting web... "
if ! systemctl start dino-web; then
    echo "error: could not start dino-web"
    exit 1
fi

echo "deployment done!"
