#!/usr/bin/env bash
netstat -s | grep "packets pruned" | awk -e '{ print $1 }'
