#!/usr/bin/env bash

echo "starting deployment..."
set -x

if [ -z $DINO_HOME ]; then
    DINO_HOME=/home/dino/dino/
fi

if [ ! -d $DINO_HOME ]; then
    echo "error: home directory '$DINO_HOME' not found"
    exit 1
fi

cd $DINO_HOME
git pull

if [ ! systemctl stop dino-web ]; then
    echo "error: could not stop dino-web"
    exit 1
fi

if [ ! systemctl stop dino-rest ]; then
    echo "error: could not stop dino-rest"
    exit 1
fi

if [ ! systemctl stop dino-app ]; then
    echo "error: could not stop dino-app"
    exit 1
fi

echo "finished stopping services, time to start them..."

if [ ! systemctl start dino-app ]; then
    echo "error: could not start dino-app"
    exit 1
fi

if [ ! systemctl start dino-rest ]; then
    echo "error: could not start dino-rest"
    exit 1
fi

if [ ! systemctl start dino-web ]; then
    echo "error: could not start dino-web"
    exit 1
fi

echo "deployment done!"
