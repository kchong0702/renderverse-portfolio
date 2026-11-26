#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."

compose() {
  docker compose -f docker-compose.yaml --profile apps "$@"
}

value() {
  sed -n "s/^$1='\(.*\)'$/\1/p" "$2"
}

healthy() {
  while read -r service port path; do
    curl -fs --max-time 5 -o /dev/null "http://$(compose port "$service" "$port" 2>/dev/null)$path" \
      || { echo "Waiting for $service" >&2; return 1; }
  done <<EOF
ops-web 8080 /
ops-api 8000 /ops-api/health
ezcareer-harness 8000 /ezcareer/health
artifact-service 8000 /artifact-service/health
ezbot 8000 /health
laya 8000 /health
otel-collector 13133 /
EOF
  [ -n "$(compose ps --status running --quiet ops-worker)" ] || { echo "Waiting for ops-worker" >&2; return 1; }
}

case "${1:-}" in
  pull)
    running=$(compose ps --all --format '{{.Image}}' ops-api | sed -n "s/.*:\(v[0-9.]*\)$/TAG='\1'/p")
    if [ "$running" != "TAG='$(value TAG .env)'" ]; then
      echo "$running" > .previous-tag
    fi
    registry=$(value REGISTRY .env)
    docker login "${registry%%/*}" --username "$2" --password-stdin
    trap 'docker logout "${registry%%/*}"' EXIT
    compose pull --quiet
    ;;
  migrate)
    compose run --rm --no-deps "$2" alembic upgrade head
    ;;
  up)
    compose up -d --remove-orphans
    ;;
  health)
    for _ in $(seq 30); do
      if healthy; then exit 0; fi
      sleep 2
    done
    if [ ! -s .previous-tag ]; then
      echo "Health check failed and there is no previous TAG to roll back to" >&2
      exit 1
    fi
    echo "Health check failed, rolling back to $(cat .previous-tag)" >&2
    { grep -v '^TAG=' .env; cat .previous-tag; } > .env.rollback
    mv .env.rollback .env
    compose up -d --remove-orphans
    exit 1
    ;;
  prune)
    registry=$(value REGISTRY .env)
    keep=" $(value TAG .env) $(value TAG .previous-tag) <none> "
    for image in $(compose config --images | grep "^$registry" | sed 's/:[^:]*$//' | sort -u); do
      for tag in $(docker image ls "$image" --format '{{.Tag}}'); do
        case "$keep" in
          *" $tag "*) ;;
          *) docker image rm "$image:$tag" ;;
        esac
      done
    done
    ;;
  *)
    echo "Usage: $0 pull USER | migrate SERVICE | up | health | prune" >&2
    exit 2
    ;;
esac
