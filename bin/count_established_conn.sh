#!/usr/bin/env bash
netstat -s | grep "connections established" | awk -e '{ print $1 }'
