#!/usr/bin/env bash

echo "starting deployment..."

TAG_NAME=$1

if [[ -z "$DINO_ENVIRONMENT" ]]; then
    echo "error: environment not set, specify using DINO_ENVIRONMENT"
    exit 1
fi

if [[ -z "$DINO_HOME" ]]; then
    echo "error: set DINO_HOME first"
    exit 1
fi

if [[ ! -d "$DINO_HOME" ]]; then
    echo "error: home directory '$DINO_HOME' not found"
    exit 1
fi

if ! cd "$DINO_HOME"; then
    echo "error: could not change to directory '$DINO_HOME'"
    exit 1
fi

if [ -z "$VIRTUAL_ENV" ]; then
    if ! source env/bin/activate; then
        echo "error: could not activate virtual environment"
        exit 1
    fi
fi

if [ ! -f .dino.yaml ]; then
    echo "error: you need to copy your dino.yaml settings to '.dino.yaml' before upgrading dino"
    exit 1
fi

SYSTEMD_PATH="/usr/lib/systemd/system"

echo "fetching new tags from git... "
if ! git fetch; then
    echo "error: could not fetch from git"
    exit 1
fi

if ! git checkout -- dino.yaml; then
    echo "error: could not clear changes to dino.yaml settings file"
    exit 1
fi

echo "switching to tag $TAG_NAME... "
if ! git checkout $TAG_NAME; then
    echo "error: could not switch to specified dino tag $TAG_NAME"
    exit 1
fi

if ! cp .dino.yaml dino.yaml; then
    echo "error: after switching tag, could not copy .dino.yaml to dino.yaml"
    exit 1
fi

if [ -f "$SYSTEMD_PATH/dino-web-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping web... "
    if ! systemctl stop dino-web-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-web"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-rest-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping rest... "
    if ! systemctl stop dino-rest-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-rest"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping app... "
    if ! systemctl stop dino-app-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-app"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-1-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping app1... "
    if ! systemctl stop dino-app-1-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-app1"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-2-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping app2... "
    if ! systemctl stop dino-app-2-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-app2"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-3-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping app3... "
    if ! systemctl stop dino-app-3-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-app3"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-4-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping app4... "
    if ! systemctl stop dino-app-4-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-app4"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-5-$DINO_ENVIRONMENT.service" ]; then
    echo "stopping app5... "
    if ! systemctl stop dino-app-5-${DINO_ENVIRONMENT}; then
        echo "error: could not stop dino-app5"
        exit 1
    fi
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

if [ -f "$SYSTEMD_PATH/dino-app-$DINO_ENVIRONMENT.service" ]; then
    echo "starting app... "
    if ! systemctl start dino-app-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-app"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-1-$DINO_ENVIRONMENT.service" ]; then
    echo "starting app1... "
    if ! systemctl start dino-app-1-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-app-1"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-2-$DINO_ENVIRONMENT.service" ]; then
    echo "starting app2... "
    if ! systemctl start dino-app-2-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-app-2"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-3-$DINO_ENVIRONMENT.service" ]; then
    echo "starting app3... "
    if ! systemctl start dino-app-3-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-app-3"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-4-$DINO_ENVIRONMENT.service" ]; then
    echo "starting app4... "
    if ! systemctl start dino-app-4-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-app-4"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-app-5-$DINO_ENVIRONMENT.service" ]; then
    echo "starting app5... "
    if ! systemctl start dino-app-5-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-app-5"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-rest-$DINO_ENVIRONMENT.service" ]; then
    echo "starting rest... "
    if ! systemctl start dino-rest-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-rest"
        exit 1
    fi
fi

if [ -f "$SYSTEMD_PATH/dino-web-$DINO_ENVIRONMENT.service" ]; then
    echo "starting web... "
    if ! systemctl start dino-web-${DINO_ENVIRONMENT}; then
        echo "error: could not start dino-web"
        exit 1
    fi
fi

echo "deployment done!"
