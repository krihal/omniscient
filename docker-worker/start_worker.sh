#!/bin/sh

cd /worker

pip3 install -r requirements.txt

echo "*******************"
echo "${CALLHOME_URL}"
echo "*******************"

python3 worker.py -u "${CALLHOME_URL}" -d -f
