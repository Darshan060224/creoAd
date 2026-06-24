#!/bin/bash
cd "$(dirname "$0")"
source ../.venv/bin/activate
rq worker ad_jobs --with-scheduler 2>&1 | tee /tmp/worker.log
