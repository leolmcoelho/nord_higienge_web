#!/bin/sh
# usage: wait_for_service.sh <url> <timeout_seconds>
URL=$1
TIMEOUT=${2:-60}
COUNT=0
while [ $COUNT -lt $TIMEOUT ]; do
  if curl -sSf "$URL" >/dev/null 2>&1; then
    echo "service available"
    exit 0
  fi
  COUNT=$((COUNT+1))
  sleep 1
done
echo "timeout waiting for $URL"
exit 1
