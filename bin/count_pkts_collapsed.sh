#!/usr/bin/env bash
netstat -s | grep "packets collapsed in receive queue due to low socket buffer$" | awk -e '{ print $1 }'

