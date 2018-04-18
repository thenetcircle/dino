#!/usr/bin/env bash
netstat -s | grep "packets pruned from receive queue because of socket buffer overrun" | awk -e '{ print $1 }'

