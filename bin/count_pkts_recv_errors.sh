#!/bin/bash
netstat -s | grep -i 'packet receive errors$' | awk '{ print $1 }'
