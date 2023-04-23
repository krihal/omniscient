#!/bin/bash

curl -s -o /dev/null -w "%{http_code}\n" https://www.sunet.se

exit 0
