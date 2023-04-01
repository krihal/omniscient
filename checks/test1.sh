#!/bin/sh

echo `ping -c1 ping.sunet.se | tail -1 | awk -F '/' '{print $5}'`

exit 0
