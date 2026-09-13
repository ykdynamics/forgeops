#!/usr/bin/env bash
# first-touch-reset.sh — return the private first-touch demo to its seeded state.
set -euo pipefail

PURGE="${FIRST_TOUCH_PURGE:-0}"

echo "== resetting the ForgeOps first-touch demo =="
for port in 8010 8011 8012 8080 8089 8093 8094 18054 18055 55454; do
  lsof -ti tcp:"$port" 2>/dev/null | xargs -r kill 2>/dev/null || true
done
docker rm -f forgeops-first-touch-pg >/dev/null 2>&1 || true
echo "stopped local services and removed the demo database container"

if [ "$PURGE" = "1" ]; then
  rm -rf /tmp/forgeops-first-touch.*
  rm -rf /tmp/forgeops-first-touch-kit.*
  rm -rf /tmp/forgeops-first-touch-ai.*
  echo "removed first-touch evidence work directories"
else
  echo "kept evidence work directories under /tmp/forgeops-first-touch.*"
fi

echo "ready to rerun ./try-forgeops or make demo-first-touch"
