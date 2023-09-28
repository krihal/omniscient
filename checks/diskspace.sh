#!/bin/bash

df -Pm . | tail -1 | awk '{print $4}'
