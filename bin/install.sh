#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

if [ $# -lt 5 ]; then
    echo "usage: $0 <environment> <dino home dir> <app/rest/web> <port>"
    echo "example: $0 production /home/dino/dino/ app 5200"
    exit 1
fi

DINO_ENVIRONMENT=$1
DINO_DIR=$2
DINO_SERVICE=$3
DINO_PORT=$4

SYSTEMD_DIR=/usr/lib/systemd/system/
SKELETON="$DINO_DIR/bin/systemd/dino-base.service.skeleton"
SCRIPT_PATH="$SYSTEMD_DIR/dino-$DINO_SERVICE-$DINO_ENVIRONMENT.service"

re='^[0-9]+$'
if ! [[ ${DINO_PORT} =~ $re ]] ; then
   echo "error: Port a number"
   exit 1
fi

if [[ ${DINO_PORT} -lt 1 || ${DINO_PORT} -gt 65536 ]]; then
    echo "error: port '${DINO_PORT}' not in range 1-65536"
    exit 1
fi

if [[ -z "$DINO_DIR" ]]; then
    DINO_DIR=/home/dino/dino/
fi

if [[ ! -d "$DINO_DIR" ]]; then
    echo "error: dino directory '$DINO_DIR' not found"
    exit 1
fi

if ! cd "$DINO_DIR"; then
    echo "error: could not change to directory '$DINO_DIR'"
    exit 1
fi

if [[ ! -d "$SYSTEMD_DIR" ]]; then
    echo "error: could not find directory '$SYSTEMD_DIR', only systemd is supported"
    exit 1
fi

process_systemd_file() {
    if [[ -f "$2" ]]; then
        echo "error: systemd script already exists at $2, aborting"
        exit 1
    fi

    if [[ ! -f "$1" ]]; then
        echo "error: can't find skeleton systemd file in bin directory: $1"
        exit 1
    fi

    if ! cp $1 $2; then
        echo "error: could not copy skeleton file to systemd directory"
        exit 1
    fi

    if ! sed -i -e "s/\${DINO_ENVIRONMENT}/$3/g" $2; then
        echo "error: could not replace a variable in systemd file $2"
        exit 1
    fi
    if ! sed -i -e "s/\${DINO_PORT}/$4/g" $2; then
        echo "error: could not replace a variable in systemd file $2"
        exit 1
    fi
    if ! sed -i -e "s/\${DINO_SERVICE}/$5/g" $2; then
        echo "error: could not replace a variable in systemd file $2"
        exit 1
    fi
}

process_systemd_file ${SKELETON} ${SCRIPT_PATH} ${DINO_ENVIRONMENT} ${DINO_PORT} ${DINO_SERVICE}
echo "finished installing systemd script in ${SCRIPT_PATH}"
