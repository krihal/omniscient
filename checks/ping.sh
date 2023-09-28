#!/bin/bash

ping -c1 192.36.125.18 | tail -1 | awk -F '/' '{print $5}'

exit 0
