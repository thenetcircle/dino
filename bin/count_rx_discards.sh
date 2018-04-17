#!/bin/bash
ethtool -S em1 | grep rx_discards | awk '{ print $2 }'
