#!/bin/bash

ping -c1 $1 | tail -1 | awk -F '/' '{print $5}'
