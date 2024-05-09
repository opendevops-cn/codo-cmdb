#!/usr/bin/env bash

sleep 1
SERVICE_NAME=$1
cd /data && python3 db_sync.py && python3 startup.py --service="${SERVICE_NAME}"