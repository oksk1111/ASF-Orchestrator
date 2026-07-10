#!/bin/bash
# Start Celery worker and beat scheduler
# Usage: ./scripts/start_celery.sh

cd "$(dirname "$0")/.."

echo "Starting Celery worker..."
celery -A app.services.fresh_alert.celery_app worker --loglevel=info &
WORKER_PID=$!

echo "Starting Celery beat..."
celery -A app.services.fresh_alert.celery_app beat --loglevel=info &
BEAT_PID=$!

echo "Worker PID: $WORKER_PID, Beat PID: $BEAT_PID"
echo "Press Ctrl+C to stop"

trap "kill $WORKER_PID $BEAT_PID; exit 0" SIGINT SIGTERM
wait
