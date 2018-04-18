#!/usr/bin/env bash
netstat -s | grep "packets pruned from receive queue$" | awk -e '{ print $1 }'

