#!/bin/bash
netstat -s | grep 'receive buffer errors$' | awk '{ print $1 }'

