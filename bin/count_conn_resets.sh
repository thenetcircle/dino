#!/bin/bash
netstat -s | grep -i 'connection resets received$' | awk '{ print $1 }'
