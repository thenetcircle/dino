#!/bin/bash
sysctl net.netfilter.nf_conntrack_count | awk '{ print $3 }'
