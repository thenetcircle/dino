#!/usr/bin/env bash
netstat -a | grep TIME_WAIT | wc -l
