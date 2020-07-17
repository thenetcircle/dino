#!/bin/bash
grep Tcp /proc/net/snmp | tail -n 1 | awk '{ print $14 }'
