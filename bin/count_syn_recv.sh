#!/usr/bin/env bash
netstat -an | grep -c SYN_RECV
