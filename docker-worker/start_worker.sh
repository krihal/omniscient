#!/bin/sh

cd /worker

pip3 install -r requirements.txt

echo "*******************"
python3 worker.py -U
echo "*******************"

python3 worker.py -u "${CALLHOME_URL}" -d -f
