#!/bin/sh

cd /worker

echo "*******************"
python3 worker.py -U
echo "*******************"

python3 worker.py -u "${CALLHOME_URL}" -d -f
