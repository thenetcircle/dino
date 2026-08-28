#!/bin/bash

if [ $# -lt 2 ]; then
    echo "usage: $0 <environment> <home path>"
    echo "example: $0 popp /home/dino/popp/"
    exit 1
fi

THE_ENV=$1
DINO_HOME=$2

#${DINO_HOME}/bin/clear_db_online_table.py ${THE_ENV} ${DINO_HOME}
#${DINO_HOME}/bin/clear_db_sessions_table.py ${THE_ENV} ${DINO_HOME}
#${DINO_HOME}/bin/clear_redis_cache.py ${THE_ENV} ${DINO_HOME}

# sleep while waiting for cloud-host-08 to clear cache and db tables
sleep 1

ps aux | grep gunicorn | grep "\-${THE_ENV}-" | grep ":app" | grep -v grep | awk '{ print $2 }' | xargs kill -HUP
