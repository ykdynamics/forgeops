#!/usr/bin/env bash
# first-touch-local.sh — control#554 first five minutes, executable locally.
#
# It demonstrates the accepted #553 journey with the canonical ForgeOps path:
# Platform Action -> Control placement/dispatch -> outbound edge session ->
# edge policy gate -> packaged ACME capability runtime -> local ACME target.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
. "$ROOT/scripts/lib-demo.sh"

PLATFORM_DIR="${PLATFORM_DIR:-}"
CAPABILITIES_DIR="${CAPABILITIES_DIR:-}"
if [ -z "$PLATFORM_DIR" ] && [ -d "$ROOT/../forgeops-platform" ]; then
  PLATFORM_DIR="$(cd "$ROOT/../forgeops-platform" && pwd)"
fi
if [ -z "$CAPABILITIES_DIR" ] && [ -d "$ROOT/../forgeops-capabilities" ]; then
  CAPABILITIES_DIR="$(cd "$ROOT/../forgeops-capabilities" && pwd)"
fi
AUTO_DECIDE="${AUTO_DECIDE:-0}"
FIRST_TOUCH_BIN_DIR="${FIRST_TOUCH_BIN_DIR:-}"
FIRST_TOUCH_METADATA="${FIRST_TOUCH_METADATA:-}"
FIRST_TOUCH_INCLUDE_MCP="${FIRST_TOUCH_INCLUDE_MCP:-0}"
# CHAT hands the requester seat to a real model instead of a script (WP-50.1).
# It brings the stack up, starts forge-chat beside the approval page, and stays
# up: from there the operations are the model's to choose and the approvals are
# a person's to make, which is the whole difference from the scripted path.
FIRST_TOUCH_CHAT="${FIRST_TOUCH_CHAT:-0}"
[ "$FIRST_TOUCH_CHAT" = "1" ] && FIRST_TOUCH_INCLUDE_MCP=1
# SCENARIO seeds one fault in the connector (WP-50.3). The scripted journey
# keeps "healthy", which is the state its assertions were written against; chat
# mode defaults to a fault, because a model handed a healthy service correctly
# declines to do anything and the demo shows nothing.
FIRST_TOUCH_SCENARIO="${FIRST_TOUCH_SCENARIO:-}"
if [ -z "$FIRST_TOUCH_SCENARIO" ]; then
  if [ "$FIRST_TOUCH_CHAT" = "1" ]; then FIRST_TOUCH_SCENARIO=stuck_queue; else FIRST_TOUCH_SCENARIO=healthy; fi
fi



CONTROL="http://127.0.0.1:8010"
PLATFORM="http://127.0.0.1:8080"
PG_PORT="${PG_PORT:-55454}"
PG_NAME="forgeops-first-touch-pg"
CALL_KEY="first-touch-call-key"
OPERATOR_TOKEN="first-touch-operator"
GATEWAY_TOKEN="first-touch-gateway"
CUSTOMER_TOKEN="${CUSTOMER_TOKEN:-forgeops-first-touch-customer-token}"
WORK="${FIRST_TOUCH_WORK:-$(mktemp -d /tmp/forgeops-first-touch.XXXXXX)}"
PIDS=()
START_EPOCH="$(date +%s)"
COMMANDS_BEFORE_READY="${FIRST_TOUCH_COMMANDS_BEFORE_READY:-1}"
CONTROL_REV="${FIRST_TOUCH_CONTROL_REV:-}"
PLATFORM_REV="${FIRST_TOUCH_PLATFORM_REV:-}"
CAPABILITIES_REV="${FIRST_TOUCH_CAPABILITIES_REV:-}"

log() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
ok() { printf '\033[1;32mOK: %s\033[0m\n' "$*"; }
fail() { echo "FIRST-TOUCH FAILED: $*" >&2; exit 1; }

# WITH is a directory holding a capability someone wrote themselves: a
# capability.yaml and the executable it describes. The demo declares it beside
# its own, hosts it on the same edge, and puts it through the same path.
#
# The manifest is read rather than a new descriptor invented, because the
# manifest is the artefact that carries the guarantees everywhere else. Two
# formats would mean the one an author learns here is not the one that governs
# their operation later.
#
# Parsed with grep, not a YAML library: this runs on machines that have python3
# and not PyYAML, which is the same reason the estate inventory is JSON.
# One place that strips surrounding quotes, so the manifest can be written with
# or without them and the parsing below stays readable.
unquote() { printf '%s' "$1" | sed -e 's/^["'"'"']//' -e 's/["'"'"']$//'; }

# PHONE makes the approval surface reachable from the local network so the
# decision can be made on a second device (#568). Off by default: the baseline
# journey is unchanged for anyone who never picks up a phone, and #553 decided
# the browser path stays the baseline precisely so a second device is never a
# prerequisite for first value.
PHONE="${FIRST_TOUCH_PHONE:-0}"

WITH="${FIRST_TOUCH_WITH:-}"
WITH_NAME=""; WITH_TARGET=""; WITH_DECISION=""; WITH_BIN=""; WITH_PORT="${FIRST_TOUCH_WITH_PORT:-8099}"
if [ -n "$WITH" ]; then
  [ -d "$WITH" ] || fail "--with $WITH is not a directory"
  man="$WITH/capability.yaml"
  [ -f "$man" ] || fail "$WITH has no capability.yaml; the manifest is what declares the operation"
  WITH_NAME="$(unquote "$(sed -n 's/^name:[[:space:]]*//p' "$man" | head -1)")"
  WITH_TARGET="$(unquote "$(sed -n 's/^[[:space:]]*-[[:space:]]*names:[[:space:]]*\[\([^]]*\)\].*/\1/p' "$man" | head -1 | cut -d, -f1 | tr -d ' ')")"
  [ -n "$WITH_NAME" ] || fail "$man declares no name:"
  [ -n "$WITH_TARGET" ] || WITH_TARGET="acme-service"
  # decision: honour an explicit one, else derive it from the declared effect.
  # A mutation defaults to ASK. That is the safer default and it is also the
  # lesson: something that changes the customer's system asks, unless someone
  # decided otherwise on purpose.
  WITH_DECISION="$(sed -n 's/^decision:[[:space:]]*//p' "$man" | head -1)"
  if [ -z "$WITH_DECISION" ]; then
    if grep -qE "^[[:space:]]*mutation:[[:space:]]*true" "$man"; then WITH_DECISION=ask; else WITH_DECISION=allow; fi
  fi
  case "$WITH_DECISION" in allow|ask|deny) ;; *) fail "decision must be allow, ask or deny, got $WITH_DECISION" ;; esac
  WITH_BIN="$(find "$WITH" -maxdepth 1 -type f -perm -111 | head -1)"
  [ -n "$WITH_BIN" ] || fail "$WITH has no executable beside capability.yaml"
fi
repo_rev() {
  local dir="$1" fallback="$2"
  if [ -d "$dir/.git" ]; then
    git -C "$dir" rev-parse HEAD
  else
    printf '%s\n' "${fallback:-unknown}"
  fi
}

# wait_mcp_tool polls the caller surface until a tool appears.
#
# The tool list is a RECONCILE against the fabric, not a fact that exists the
# moment the process listens. Asserting it once turned a surface that becomes
# correct into a demo that failed at random, and the failure said only that the
# tool was missing -- never what the list actually held, which is the one thing
# needed to tell "not yet" from "not ever".
wait_mcp_tool() {
  local tool="$1" seen=""
  for _ in $(seq 1 20); do
    seen="$("$WORK/forgectl" mcp list --server http://127.0.0.1:18055 2>&1 || true)"
    printf '%s\n' "$seen" | grep -q "^${tool}\$" && return 0
    sleep 0.5
  done
  fail "MCP tool list never exposed $tool; it held: ${seen:-<empty>}"
}

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
  docker rm -f "$PG_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

mkdir -p "$WORK"

if [ -n "$FIRST_TOUCH_METADATA" ] && [ -f "$FIRST_TOUCH_METADATA" ]; then
  # shellcheck disable=SC1090
  . "$FIRST_TOUCH_METADATA"
fi
CONTROL_REV="${CONTROL_REV:-${FIRST_TOUCH_CONTROL_REV:-}}"
PLATFORM_REV="${PLATFORM_REV:-${FIRST_TOUCH_PLATFORM_REV:-}}"
CAPABILITIES_REV="${CAPABILITIES_REV:-${FIRST_TOUCH_CAPABILITIES_REV:-}}"

if [ -z "$FIRST_TOUCH_BIN_DIR" ]; then
  [ -d "$PLATFORM_DIR" ] || fail "forgeops-platform not found at $PLATFORM_DIR (set PLATFORM_DIR)"
  [ -d "$CAPABILITIES_DIR" ] || fail "forgeops-capabilities not found at $CAPABILITIES_DIR (set CAPABILITIES_DIR)"
fi

request_json() {
  local method="$1" url="$2" token="$3" body="${4:-}"
  if [ -n "$body" ]; then
    curl -fsS -X "$method" "$url" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' -d "$body"
  else
    curl -fsS -X "$method" "$url" -H "Authorization: Bearer $token"
  fi
}

state_json() { curl -fsS "http://127.0.0.1:8089/state"; }
state_field() {
  state_json | python3 -c "import json,sys; print(json.load(sys.stdin).get('$1',''))"
}
action_status() {
  request_json GET "$PLATFORM/v1/tenants/$TENANT/actions/$1" "$REQUESTER_JWT" |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))'
}
action_status_for() {
  request_json GET "$PLATFORM/v1/tenants/$TENANT/actions/$1" "$2" |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))'
}
wait_status() {
  local action="$1" want="$2" status=""
  for _ in $(seq 1 80); do
    status="$(action_status "$action")"
    [ "$status" = "$want" ] && { echo "$status"; return 0; }
    case "$status" in failed|refused|denied|expired|succeeded)
      [ "$status" = "$want" ] && { echo "$status"; return 0; }
      ;;
    esac
    sleep 0.5
  done
  echo "$status"
  return 1
}
wait_terminal() {
  local action="$1" status=""
  for _ in $(seq 1 80); do
    status="$(action_status "$action")"
    case "$status" in succeeded|failed|denied|refused|expired)
      echo "$status"
      return 0
      ;;
    esac
    sleep 0.5
  done
  echo "$status"
  return 1
}
wait_terminal_for() {
  local action="$1" token="$2" status=""
  for _ in $(seq 1 80); do
    status="$(action_status_for "$action" "$token")"
    case "$status" in succeeded|failed|denied|refused|expired)
      echo "$status"
      return 0
      ;;
    esac
    sleep 0.5
  done
  echo "$status"
  return 1
}
proposal_for() {
  request_json GET "$PLATFORM/v1/tenants/$TENANT/proposals?workspace_id=ws-1" "$APPROVER_JWT" |
    python3 -c "import json,sys; d=json.load(sys.stdin); print(next((p['proposal_id'] for p in d.get('proposals',[]) if p.get('action_id')=='$1'), ''))"
}
decide() {
  local proposal="$1" decision="$2"
  request_json POST "$PLATFORM/v1/tenants/$TENANT/proposals/$proposal/decide" "$APPROVER_JWT" \
    "{\"decision\":\"$decision\",\"note\":\"first-touch $decision\"}" >/dev/null
}
make_action() {
  local cap="$1" idem="$2" purpose="$3" input="$4"
  request_json POST "$PLATFORM/v1/tenants/$TENANT/actions" "$REQUESTER_JWT" \
    "{\"workspace_id\":\"ws-1\",\"capability_uid\":\"$cap\",\"capability_revision\":1,\"target\":\"acme-service\",\"input\":$input,\"policy_revision\":$POLICY_REV,\"idempotency_key\":\"$idem\",\"max_attempts\":1,\"request_purpose\":\"$purpose\"}" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["action_id"])'
}

if [ -n "$FIRST_TOUCH_BIN_DIR" ]; then
  log "using the bundled ForgeOps runtime"
  for n in forge-control forge-agent forgectl api acme-service acme-service-status acme-service-restart acme-service-resync; do
    [ -x "$FIRST_TOUCH_BIN_DIR/$n" ] || fail "bundle is missing executable bin/$n"
    ln -sf "$FIRST_TOUCH_BIN_DIR/$n" "$WORK/$n"
  done
  if [ "$FIRST_TOUCH_INCLUDE_MCP" = "1" ]; then
    [ -x "$FIRST_TOUCH_BIN_DIR/forge-mcp" ] || fail "bundle is missing executable bin/forge-mcp"
    ln -sf "$FIRST_TOUCH_BIN_DIR/forge-mcp" "$WORK/forge-mcp"
  fi
  # The approval surface serves BOTH journeys now, so it is not chat-only.
  [ -x "$FIRST_TOUCH_BIN_DIR/forge-approval-ui" ] || fail "bundle is missing executable bin/forge-approval-ui"
  ln -sf "$FIRST_TOUCH_BIN_DIR/forge-approval-ui" "$WORK/forge-approval-ui"
  if [ "$FIRST_TOUCH_CHAT" = "1" ]; then
    [ -x "$FIRST_TOUCH_BIN_DIR/forge-chat" ] || fail "bundle is missing executable bin/forge-chat"
    ln -sf "$FIRST_TOUCH_BIN_DIR/forge-chat" "$WORK/forge-chat"
  fi
  ok "bundled runtime ready"
else
  log "building current local binaries"
  go build -o "$WORK/forge-control" ./cmd/forge-control
  go build -o "$WORK/forge-agent" ./cmd/forge-agent
  go build -o "$WORK/forgectl" ./cmd/forgectl
  if [ "$FIRST_TOUCH_INCLUDE_MCP" = "1" ]; then
    go build -o "$WORK/forge-mcp" ./cmd/forge-mcp
  fi
  go build -o "$WORK/forge-approval-ui" ./cmd/forge-approval-ui
  if [ "$FIRST_TOUCH_CHAT" = "1" ]; then
    go build -o "$WORK/forge-chat" ./cmd/forge-chat
  fi
  (cd "$PLATFORM_DIR" && go build -o "$WORK/api" ./cmd/api)
  for n in acme-service acme-service-status acme-service-restart acme-service-resync; do
    (cd "$CAPABILITIES_DIR" && go build -trimpath -buildvcs=false -o "$WORK/$n" "./cmd/$n")
  done
  ok "binaries built"
fi

log "preparing local ports"
for port in 8010 8011 8012 8080 8089 8093 8094 8095 18054 18055 18056 18057 "$PG_PORT"; do
  lsof -ti tcp:"$port" 2>/dev/null | xargs -r kill 2>/dev/null || true
done
docker rm -f "$PG_NAME" >/dev/null 2>&1 || true
sleep 1

log "starting Postgres, Platform and Control"
docker run -d --name "$PG_NAME" -e POSTGRES_USER=forgeops -e POSTGRES_PASSWORD=forgeops \
  -e POSTGRES_DB=forgeops_control -p "127.0.0.1:$PG_PORT:5432" postgres:16-alpine >/dev/null
for _ in $(seq 1 30); do docker exec "$PG_NAME" pg_isready -U forgeops >/dev/null 2>&1 && break; sleep 1; done
docker exec "$PG_NAME" createdb -U forgeops forgeops_shard >/dev/null 2>&1 || true
CONTROL_DB_DSN="postgres://forgeops:forgeops@127.0.0.1:$PG_PORT/forgeops_control?sslmode=disable"
SHARD_DB_DSN="postgres://forgeops:forgeops@127.0.0.1:$PG_PORT/forgeops_shard?sslmode=disable"

demo_start_process PLATFORM_PID platform "$WORK/platform.log" 8080 -- \
  env CONTROL_DB_DSN="$CONTROL_DB_DSN" SHARD_DB_DSN="$SHARD_DB_DSN" \
    OPERATOR_TOKEN="$OPERATOR_TOKEN" API_PORT=8080 API_ENV=production \
    CONTROL_GATEWAY_BASE_URL="$CONTROL" CONTROL_GATEWAY_TOKEN="$GATEWAY_TOKEN" \
    CONTROL_PLACEMENT_CONTRACT=canonical APPROVAL_GRANT_VERSION=2 \
    OIDC_ISSUER="" OIDC_AUDIENCE="forgeops-approval-pwa" \
    APPROVAL_POLICY_REVISION=1 KAFKA_BROKERS="" "$WORK/api"
PIDS+=("$PLATFORM_PID")
demo_wait_http_ready platform "$PLATFORM_PID" "$PLATFORM/health/ready" "$WORK/platform.log"

curl -fsS -o "$WORK/signing-keys.json" "$PLATFORM/v1/operator/signing/keys" -H "Authorization: Bearer $OPERATOR_TOKEN"
python3 -c "import json; print(json.load(open('$WORK/signing-keys.json'))['keys'][0]['public_key_pem'])" > "$WORK/approval-trust.pem"
grep -q "PUBLIC KEY" "$WORK/approval-trust.pem" || fail "no approval public key published"
# WP-39.5 canonical-input enforcement is ON here. Without it the demo announced
# "canonical-input enforcement OFF (migration window): placements without the
# authorized executable input are accepted and counted" as the first thing an
# evaluator reads about a system whose claim is that the customer's authority
# decides what executes.
demo_start_process CONTROL_PID forge-control "$WORK/control.log" 8010 8012 -- \
  "$WORK/forge-control" --listen :8010 --session-addr :8012 \
    --call-key "$CALL_KEY" --operator-token "$OPERATOR_TOKEN" \
    --gateway-token "$GATEWAY_TOKEN" --platform-approval-trust "$WORK/approval-trust.pem" \
    --enforce-canonical-input \
    --grant-audience forgeops-edge --platform-url "$PLATFORM" --platform-token "$GATEWAY_TOKEN" \
    --state-file "$WORK/control-state.json"
PIDS+=("$CONTROL_PID")
demo_wait_http_ready forge-control "$CONTROL_PID" "$CONTROL/readyz" "$WORK/control.log"
# Assert the posture rather than trusting the flags: a renamed flag, or a
# default that quietly reverts, would otherwise put the demo back in the
# migration window while every step still passed. The three outcomes this
# script proves are only worth what the enforcement behind them is worth.
grep -q "canonical-input enforcement ON" "$WORK/control.log" ||
  fail "control did not enforce canonical input; the demo would accept a placement carrying no authorized executable input"
ok "Platform and Control ready; canonical-input enforcement ON"

# Three declarations, not one. A capability that exists and is permitted still
# cannot run unless the EDGE says it hosts it -- the customer's side decides
# what may execute there, and placement refuses with no_eligible_agent if it
# does not. That refusal is the authority model working, so the fragments are
# built together and the reason is stated here rather than discovered.
WITH_RESOURCE=""; WITH_AGENT_ENTRY=""; WITH_BINDING=""
if [ -n "$WITH" ]; then
  WITH_AGENT_ENTRY=", $WITH_NAME"
  WITH_BINDING="
    - capabilities: [$WITH_NAME]
      agent: first-touch-edge
      decision: $WITH_DECISION"
  WITH_RESOURCE="---
kind: Capability
metadata:
  name: $WITH_NAME
spec:
  interface: mcp
  target: $WITH_TARGET
"
fi

log "declaring the first-touch fabric"
export FORGE_OPERATOR_TOKEN="$OPERATOR_TOKEN"
FORGE_API_KEY="$("$WORK/forgectl" api-key issue first-touch | awk '/Bearer /{print $NF}')"
export FORGE_API_KEY
# Unquoted heredoc: the three WITH_ fragments have to expand. Nothing else in
# this document contains a dollar sign, so nothing else is at risk of being
# treated as a variable.
cat > "$WORK/first-touch.yaml" <<YAML
apiVersion: forgeops.io/v1
kind: Environment
metadata:
  name: first-touch
spec:
  slug: first-touch
---
apiVersion: forgeops.io/v1
kind: Capability
metadata:
  name: acme.service.status
spec:
  interface: mcp
  target: acme-service
---
apiVersion: forgeops.io/v1
kind: Capability
metadata:
  name: acme.service.restart
spec:
  interface: mcp
  target: acme-service
  requiredSecrets: [SERVICE_TOKEN]
---
apiVersion: forgeops.io/v1
kind: Capability
metadata:
  name: acme.service.resync
spec:
  interface: mcp
  target: acme-service
  requiredSecrets: [SERVICE_TOKEN]
---
apiVersion: forgeops.io/v1
kind: Capability
metadata:
  name: acme.service.shell
spec:
  interface: mcp
  target: acme-service
${WITH_RESOURCE}---
apiVersion: forgeops.io/v1
kind: Agent
metadata:
  name: first-touch-edge
spec:
  environment: first-touch
  capabilities: [acme.service.status, acme.service.restart, acme.service.resync, acme.service.shell${WITH_AGENT_ENTRY}]
---
apiVersion: forgeops.io/v1
kind: Policy
metadata:
  name: first-touch
spec:
  bindings:
    - capabilities: [acme.service.status]
      agent: first-touch-edge
      decision: allow
    - capabilities: [acme.service.restart]
      agent: first-touch-edge
      decision: ask
    - capabilities: [acme.service.resync]
      agent: first-touch-edge
      decision: ask
    - capabilities: [acme.service.shell]
      agent: first-touch-edge
      decision: deny${WITH_BINDING}
YAML
"$WORK/forgectl" apply -f "$WORK/first-touch.yaml"

log "starting ACME Sync Connector, capability runtimes and edge"
printf 'SERVICE_TOKEN=%s\n' "$CUSTOMER_TOKEN" > "$WORK/secrets.env"
chmod 600 "$WORK/secrets.env"
demo_start_process ACME_PID acme-service "$WORK/acme-service.log" 8089 -- \
  env ACME_SERVICE_ADDR=":8089" ACME_SERVICE_TOKEN="$CUSTOMER_TOKEN" ACME_PENDING_JOBS=17 ACME_CONFIG_VERSION=v4 \
    ACME_SCENARIO="$FIRST_TOUCH_SCENARIO" "$WORK/acme-service"
PIDS+=("$ACME_PID")
demo_wait_http_ready acme-service "$ACME_PID" "http://127.0.0.1:8089/state" "$WORK/acme-service.log"

demo_start_process STATUS_PID acme-service-status "$WORK/acme-status.log" 8093 -- \
  env ACME_SERVICE_TARGETS="acme-service=http://127.0.0.1:8089" ACME_STATUS_ALLOWLIST="http://127.0.0.1:8089" CAPABILITY_ADDR=":8093" "$WORK/acme-service-status"
PIDS+=("$STATUS_PID")
demo_wait_http_ready acme-service-status "$STATUS_PID" "http://127.0.0.1:8093/health" "$WORK/acme-status.log"

demo_start_process RESTART_PID acme-service-restart "$WORK/acme-restart.log" 8094 -- \
  env ACME_SERVICE_TARGETS="acme-service=http://127.0.0.1:8089" ACME_RESTART_ALLOWLIST="http://127.0.0.1:8089" CAPABILITY_ADDR=":8094" "$WORK/acme-service-restart"
PIDS+=("$RESTART_PID")
demo_wait_http_ready acme-service-restart "$RESTART_PID" "http://127.0.0.1:8094/health" "$WORK/acme-restart.log"

# The second mutation (WP-50.3). It is what makes the restart a CHOICE: without
# an alternative, an AI asked to fix something has one button and no diagnosis
# to make.
demo_start_process RESYNC_PID acme-service-resync "$WORK/acme-resync.log" 8095 -- \
  env ACME_SERVICE_TARGETS="acme-service=http://127.0.0.1:8089" ACME_RESYNC_ALLOWLIST="http://127.0.0.1:8089" CAPABILITY_ADDR=":8095" "$WORK/acme-service-resync"
PIDS+=("$RESYNC_PID")
demo_wait_http_ready acme-service-resync "$RESYNC_PID" "http://127.0.0.1:8095/health" "$WORK/acme-resync.log"

WITH_RUNTIME_FLAG=""
if [ -n "$WITH" ]; then
  demo_start_process WITH_PID "$WITH_NAME" "$WORK/with-capability.log" "$WITH_PORT" -- \
    env CAPABILITY_ADDR=":$WITH_PORT" "$WITH_BIN"
  PIDS+=("$WITH_PID")
  WITH_RUNTIME_FLAG="--capability-runtime $WITH_NAME=http://127.0.0.1:$WITH_PORT"
fi

AGENT_TOKEN="$("$WORK/forgectl" issue agent first-touch-edge | tail -1)"
demo_start_process AGENT_PID forge-agent "$WORK/agent.log" 8011 -- \
  "$WORK/forge-agent" --name first-touch-edge --control "$CONTROL" \
    --listen http://127.0.0.1:8011 --listen-addr 127.0.0.1:8011 \
    --token "$AGENT_TOKEN" --control-key "$CALL_KEY" --session-addr "127.0.0.1:8012" \
    --hold-timeout 10m --secrets-file "$WORK/secrets.env" --environment first-touch \
    --spool-dir "$WORK/agent-spool" --platform-approval-trust "$WORK/approval-trust.pem" \
    --grant-audience forgeops-edge \
    --capability-runtime acme.service.status="http://127.0.0.1:8093" \
    --capability-runtime acme.service.restart="http://127.0.0.1:8094" \
    --capability-runtime acme.service.resync="http://127.0.0.1:8095" \
    ${WITH_RUNTIME_FLAG}
PIDS+=("$AGENT_PID")
for _ in $(seq 1 80); do
  phase="$("$WORK/forgectl" get agents 2>/dev/null | awk '$1=="first-touch-edge"{print $3}')"
  [ "$phase" = "Ready" ] && break
  sleep 0.5
done
[ "${phase:-}" = "Ready" ] || fail "first-touch-edge did not reach Ready; see $WORK/agent.log"
ok "first-touch-edge Ready"
READY_EPOCH="$(date +%s)"

log "provisioning requester and customer-approver identities"
TENANT="$(curl -fsS -X POST "$PLATFORM/v1/tenants" -H "Authorization: Bearer $OPERATOR_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"First Touch Tenant","slug":"first-touch"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
raw_requester="$(curl -fsS -X POST "$PLATFORM/v1/tenants/$TENANT/api-keys" -H "Authorization: Bearer $OPERATOR_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"acme-requester","roles":["member"],"workspace_id":"ws-1","capability_scope":["acme.service."]}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["key"])')"
raw_approver="$(curl -fsS -X POST "$PLATFORM/v1/tenants/$TENANT/api-keys" -H "Authorization: Bearer $OPERATOR_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"customer-approver","roles":["approver"],"workspace_id":"ws-1"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["key"])')"
REQUESTER_JWT="$(curl -fsS -X POST "$PLATFORM/v1/auth/token" -H 'Content-Type: application/json' -d "{\"api_key\":\"$raw_requester\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
APPROVER_JWT="$(curl -fsS -X POST "$PLATFORM/v1/auth/token" -H 'Content-Type: application/json' -d "{\"api_key\":\"$raw_approver\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
request_json POST "$PLATFORM/v1/tenants/$TENANT/workspaces" "$REQUESTER_JWT" '{"name":"ws-1","slug":"ws-1"}' >/dev/null
POLICY_REV="$(curl -fsS "$CONTROL/readyz" | python3 -c 'import json,sys; print(json.load(sys.stdin)["policyRevision"])')"
ok "requester and approver identities are distinct; policy revision $POLICY_REV"

# The real customer approval surface (forgeops-approval-pwa), served with the
# single origin it needs: it calls Platform at /v1, and Platform sends no CORS
# header at all, so the browser must see one host for both.
#
# The session is handed over in the URL FRAGMENT. Fragments are not sent to
# servers and do not reach access logs, so the approver's token does not pass
# through this process's records on its way to the tab that needs it. The PWA
# strips it as soon as it adopts it.
PWA_DIR_FT="${PWA_DIR_FT:-}"
if [ -z "$PWA_DIR_FT" ]; then
  if [ -n "$FIRST_TOUCH_BIN_DIR" ] && [ -d "$(dirname "$FIRST_TOUCH_BIN_DIR")/pwa" ]; then
    PWA_DIR_FT="$(cd "$(dirname "$FIRST_TOUCH_BIN_DIR")/pwa" && pwd)"
  elif [ -d "$ROOT/../forgeops-approval-pwa/dist" ]; then
    PWA_DIR_FT="$(cd "$ROOT/../forgeops-approval-pwa/dist" && pwd)"
  fi
fi
if [ -n "$PWA_DIR_FT" ] && [ -f "$PWA_DIR_FT/index.html" ]; then
  demo_start_process PWAUI_PID forge-approval-ui "$WORK/forge-approval-ui.log" 18057 -- \
    "$WORK/forge-approval-ui" --dir "$PWA_DIR_FT" --platform "$PLATFORM" --listen 127.0.0.1:18057
  PIDS+=("$PWAUI_PID")
  demo_wait_http_ready forge-approval-ui "$PWAUI_PID" "http://127.0.0.1:18057/" "$WORK/forge-approval-ui.log"
  # A REAL credential with the approver role, distinct from the AI
  # requester's. Platform validates it, derives the approver from it, and
  # refuses a decision from anything that does not carry the role.
  #
  # The workspace is named because this credential is workspace-SCOPED, and
  # Platform refuses a tenant-wide list from one that is ("workspace scope
  # mismatch"). A handover that left it out produced a session the PWA used
  # to list across the tenant, which the server correctly rejected.
  PWA_HANDOVER="$(python3 -c 'import base64, json, sys; print(base64.urlsafe_b64encode(json.dumps({"token": sys.argv[1], "tenant_id": sys.argv[2], "workspace_id": "ws-1", "subject": "customer-approver", "roles": ["approver"]}).encode()).decode().rstrip("="))' "$APPROVER_JWT" "$TENANT")"
  PWA_URL="http://127.0.0.1:18057/#ft=$PWA_HANDOVER"
else
  PWA_URL=""
fi


# One approval surface for both journeys. The simple page written for this demo
# survives only where the PWA cannot go: PHONE=1 serves a per-proposal link to a
# second device on the LAN, and the PWA is bound to loopback here.
FIRST_TOUCH_SIMPLE_APPROVAL=0
[ -z "$PWA_URL" ] && FIRST_TOUCH_SIMPLE_APPROVAL=1
[ "$PHONE" = "1" ] && FIRST_TOUCH_SIMPLE_APPROVAL=1

# What the scripted journey tells a human to open. One name for it, so the two
# journeys in this bundle never describe different surfaces to the same reader.
APPROVAL_SURFACE="${PWA_URL:-http://127.0.0.1:18054/}"

if [ "$FIRST_TOUCH_SIMPLE_APPROVAL" = "1" ]; then
log "starting the browser approval surface"
demo_start_process APPROVAL_PID approval-server "$WORK/approval-server.log" 18054 -- \
  env FIRST_TOUCH_PLATFORM="$PLATFORM" FIRST_TOUCH_TENANT="$TENANT" FIRST_TOUCH_WORKSPACE=ws-1 \
    FIRST_TOUCH_APPROVER_JWT="$APPROVER_JWT" FIRST_TOUCH_APPROVAL_PORT=18054 \
    FIRST_TOUCH_PHONE="$PHONE" \
    python3 "$ROOT/scripts/first-touch-approval-server.py"
PIDS+=("$APPROVAL_PID")
demo_wait_http_ready approval-server "$APPROVAL_PID" "http://127.0.0.1:18054/" "$WORK/approval-server.log"
if [ "$PHONE" = "1" ]; then
  ok "approval page: http://127.0.0.1:18054/ — each held operation also shows a link for a phone on this network"
else
  ok "approval page: http://127.0.0.1:18054/"
fi
fi
if [ -n "$PWA_URL" ] && [ "$FIRST_TOUCH_SIMPLE_APPROVAL" = "0" ]; then
  ok "approval surface: the ForgeOps Approval PWA (link printed when an operation is held)"
fi

if [ "$FIRST_TOUCH_CHAT" = "1" ]; then
  # WP-50.1: the requester seat goes to a real model, and it goes there NOW.
  # Nothing below this point runs: the scripted journey is what the model
  # replaces, and making an evaluator click through it first would put the
  # thing they came to see behind two approvals they did not ask to make.
  #
  # The model gets the workspace Action credential through forge-mcp and
  # nothing else. It does not get the approver JWT (that stays in the approval
  # server), the customer token (that stays in the edge secrets file and the
  # ACME target env), or a route to the target.
  log "handing the requester seat to a model"
  raw_ai="$(curl -fsS -X POST "$PLATFORM/v1/tenants/$TENANT/api-keys" -H "Authorization: Bearer $OPERATOR_TOKEN" -H 'Content-Type: application/json' \
    -d '{"name":"ai-caller","roles":["member"],"workspace_id":"ws-1","capability_scope":["acme.service."]}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["key"])')"
  AI_JWT="$(curl -fsS -X POST "$PLATFORM/v1/auth/token" -H 'Content-Type: application/json' -d "{\"api_key\":\"$raw_ai\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
  demo_start_process MCP_PID forge-mcp "$WORK/forge-mcp.log" 18055 -- \
    "$WORK/forge-mcp" --control "$CONTROL" --platform "$PLATFORM" \
      --platform-token "$AI_JWT" --api-key "$FORGE_API_KEY" --listen :18055
  PIDS+=("$MCP_PID")
  demo_wait_http_ready forge-mcp "$MCP_PID" "http://127.0.0.1:18055/mcp/tools" "$WORK/forge-mcp.log"
  wait_mcp_tool acme_service_status

  # The policy this edge enforces is a file the evaluator can edit, and the
  # apply command carries the operator credentials so editing it is one step
  # rather than a credential hunt. They still make the edit themselves: a
  # script that flips the rule for them proves less than watching their own
  # change reach the edge.
  cat > "$WORK/apply-policy" <<APPLY
#!/usr/bin/env bash
set -euo pipefail
export FORGE_OPERATOR_TOKEN="$OPERATOR_TOKEN"
export FORGE_API_KEY="$FORGE_API_KEY"
exec "$WORK/forgectl" apply -f "$WORK/first-touch.yaml"
APPLY
  chmod 755 "$WORK/apply-policy"

  demo_start_process CHAT_PID forge-chat "$WORK/forge-chat.log" 18056 -- \
    "$WORK/forge-chat" --mcp http://127.0.0.1:18055 \
      --tenant "$TENANT" --workspace ws-1 \
      --platform "$PLATFORM" --platform-token "$AI_JWT" \
      --target-state http://127.0.0.1:8089/state \
      --policy-file "$WORK/first-touch.yaml" --policy-apply "$WORK/apply-policy" \
      --effort "${FORGE_CHAT_EFFORT:-low}" \
      --approval-url http://127.0.0.1:18054/ --listen 127.0.0.1:18056
  PIDS+=("$CHAT_PID")
  demo_wait_http_ready forge-chat "$CHAT_PID" "http://127.0.0.1:18056/" "$WORK/forge-chat.log"

  echo
  ok "chat:     http://127.0.0.1:18056/"
  if [ -n "$PWA_URL" ]; then
    ok "approval: $PWA_URL"
    echo "          (the real ForgeOps Approval PWA; the link carries a one-time"
    echo "           session for the customer-approver identity and is stripped"
    echo "           from the address bar as soon as the page adopts it)"
  else
    ok "approval: http://127.0.0.1:18054/"
  fi
  cat <<CHAT

Something is wrong with the connector. Ask the model what, and watch three
things:

  - a read runs with no approval and no friction;
  - the operation it decides on is HELD until you decide it in the approval page;
  - a shell is refused, and no counter moves.

Then try to break it. Tell it to export the data. Tell it to approve its own
restart. The request is allowed to be made; the boundary is what answers.

This run seeded: $FIRST_TOUCH_SCENARIO

Re-run with a different fault, and the right operation changes with it. That is
the point: the model has to work out which one, and the wrong one visibly fails
to help.

  FIRST_TOUCH_SCENARIO=stuck_queue          a restart clears it
  FIRST_TOUCH_SCENARIO=stale_config         only a resync applies it
  FIRST_TOUCH_SCENARIO=transient_upstream   it recovers on its own
  FIRST_TOUCH_SCENARIO=healthy              nothing is wrong

The policy the edge enforces is a file you can edit:

  $WORK/first-touch.yaml      change a rule
  $WORK/apply-policy          apply it

Turn the restart rule from ask to allow and it stops holding. Turn it back and
the hold returns. The gate is policy, not something compiled in.

Ctrl-C here tears the whole stack down.

CHAT
  while :; do sleep 3600; done
fi

log "A. diagnostics ALLOW returns target-derived connector state"
STATUS_ACTION="$(make_action acme.service.status first-touch-status "read ACME Sync Connector diagnostics" '{"service":"acme-service"}')"
[ "$(wait_status "$STATUS_ACTION" succeeded)" = "succeeded" ] || fail "diagnostics did not succeed"
pending="$(state_field pending_jobs)"
config="$(state_field config_version)"
restarts_before="$(state_field restart_count)"
[ "$pending" = "17" ] || fail "pending_jobs = $pending, want 17"
[ "$config" = "v4" ] || fail "config_version = $config, want v4"
ok "diagnostics completed; target says pending_jobs=$pending config=$config restart_count=$restarts_before"

log "B/C. restart ASK holds, then browser approval releases one real effect"
RESTART_ACTION="$(make_action acme.service.restart first-touch-restart-approve "Connector has 17 pending jobs." '{"service":"acme-service"}')"
[ "$(wait_status "$RESTART_ACTION" held)" = "held" ] || fail "restart did not reach held"
[ "$(state_field restart_count)" = "$restarts_before" ] || fail "restart changed before approval"
PROP="$(proposal_for "$RESTART_ACTION")"
[ -n "$PROP" ] || fail "no proposal for held restart"
if [ "$AUTO_DECIDE" = "1" ]; then
  decide "$PROP" approve
else
  echo
  echo "Open ${APPROVAL_SURFACE} and approve proposal $PROP."
  for _ in $(seq 1 600); do
    [ "$(action_status "$RESTART_ACTION")" != "held" ] && break
    sleep 1
  done
fi
[ "$(wait_status "$RESTART_ACTION" succeeded)" = "succeeded" ] || fail "approved restart did not succeed"
restarts_after="$(state_field restart_count)"
[ "$restarts_after" = "$((restarts_before + 1))" ] || fail "restart_count $restarts_before -> $restarts_after, want one effect"
receipt="$(state_field last_restart_receipt)"
case "$receipt" in *"$RESTART_ACTION"*) ok "restart approved and executed exactly once; receipt=$receipt" ;; *) fail "receipt does not name action: $receipt" ;; esac

log "D. denying a held restart produces zero target effect"
REJECT_ACTION="$(make_action acme.service.restart first-touch-restart-deny "second restart request to prove Deny leaves the connector unchanged" '{"service":"acme-service"}')"
[ "$(wait_status "$REJECT_ACTION" held)" = "held" ] || fail "second restart did not reach held"
PROP_DENY="$(proposal_for "$REJECT_ACTION")"
[ -n "$PROP_DENY" ] || fail "no proposal for denied restart"
if [ "$AUTO_DECIDE" = "1" ]; then
  decide "$PROP_DENY" reject
else
  echo
  echo "Open ${APPROVAL_SURFACE} and reject proposal $PROP_DENY."
  for _ in $(seq 1 600); do
    [ "$(action_status "$REJECT_ACTION")" != "held" ] && break
    sleep 1
  done
fi
reject_status="$(wait_terminal "$REJECT_ACTION")"
case "$reject_status" in failed|denied|refused|expired) ;; *) fail "denied restart did not reach a terminal refusal (status $reject_status)" ;; esac
[ "$(state_field restart_count)" = "$restarts_after" ] || fail "denied restart changed target state"
ok "denied restart ended $reject_status and produced zero target effect"

log "E. shell access DENY refuses by policy with zero effect"
SHELL_ACTION="$(make_action acme.service.shell first-touch-shell "request arbitrary shell access" '{"command":"whoami"}')"
[ "$(wait_status "$SHELL_ACTION" failed)" = "failed" ] || fail "shell action did not fail"
shell_reason="$(request_json GET "$PLATFORM/v1/tenants/$TENANT/actions/$SHELL_ACTION/explain" "$REQUESTER_JWT" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("action") or {}).get("failure_reason",""))')"
case "$shell_reason" in *"denied by edge policy"*) ok "shell refused by authority: $shell_reason" ;; *) fail "shell refusal was not policy denial: ${shell_reason:-<none>}" ;; esac
[ "$(state_field restart_count)" = "$restarts_after" ] || fail "shell denial changed target state"

if [ -n "$WITH" ]; then
  log "Z. $WITH_NAME — an operation you wrote, through the same path"
  WITH_ACTION="$(make_action "$WITH_NAME" "with-capability-1" "first run of an operation written outside this demo" '{"service":"'"$WITH_TARGET"'"}')"
  case "$WITH_DECISION" in
    deny)
      [ "$(wait_terminal "$WITH_ACTION")" = "failed" ] || fail "$WITH_NAME was declared deny but did not fail"
      ok "$WITH_NAME was refused by the edge policy you declared, and nothing ran"
      ;;
    ask)
      [ "$(wait_status "$WITH_ACTION" held)" = "held" ] || fail "$WITH_NAME was declared ask but never held"
      WITH_PROP="$(proposal_for "$WITH_ACTION")"
      [ -n "$WITH_PROP" ] || fail "no proposal for $WITH_NAME"
      if [ "$AUTO_DECIDE" = "1" ]; then
        decide "$WITH_PROP" approve
      else
        echo
        echo "Open ${APPROVAL_SURFACE} and approve proposal $WITH_PROP."
        for _ in $(seq 1 600); do
          [ "$(action_status "$WITH_ACTION")" != "held" ] && break
          sleep 1
        done
      fi
      [ "$(wait_status "$WITH_ACTION" succeeded)" = "succeeded" ] || fail "$WITH_NAME did not succeed after approval"
      ok "$WITH_NAME held for a human, then ran once — your operation, the customer's decision"
      ;;
    *)
      [ "$(wait_status "$WITH_ACTION" succeeded)" = "succeeded" ] || fail "$WITH_NAME did not succeed"
      ok "$WITH_NAME succeeded through Platform, Control, the edge policy gate and your runtime"
      ;;
  esac
fi

log "F. requester has no direct credential path used by the scenario"
if grep -q "$CUSTOMER_TOKEN" "$WORK/approval-server.log" "$WORK/control.log" "$WORK/platform.log" 2>/dev/null; then
  fail "customer token leaked into requester/control/platform logs"
fi
ok "customer token stayed in edge secrets file and ACME target env; requester used only Platform Actions"

if [ "$FIRST_TOUCH_INCLUDE_MCP" = "1" ]; then
  log "G. AI/MCP requester uses the same authority path"
  raw_ai="$(curl -fsS -X POST "$PLATFORM/v1/tenants/$TENANT/api-keys" -H "Authorization: Bearer $OPERATOR_TOKEN" -H 'Content-Type: application/json' \
    -d '{"name":"ai-caller","roles":["member"],"workspace_id":"ws-1","capability_scope":["acme.service."]}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["key"])')"
  AI_JWT="$(curl -fsS -X POST "$PLATFORM/v1/auth/token" -H 'Content-Type: application/json' -d "{\"api_key\":\"$raw_ai\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
  demo_start_process MCP_PID forge-mcp "$WORK/forge-mcp.log" 18055 -- \
    "$WORK/forge-mcp" --control "$CONTROL" --platform "$PLATFORM" \
      --platform-token "$AI_JWT" --api-key "$FORGE_API_KEY" --listen :18055
  PIDS+=("$MCP_PID")
  demo_wait_http_ready forge-mcp "$MCP_PID" "http://127.0.0.1:18055/mcp/tools" "$WORK/forge-mcp.log"
  wait_mcp_tool acme_service_status

  mcp_status="$("$WORK/forgectl" mcp call --server http://127.0.0.1:18055 acme_service_status \
    "{\"service\":\"acme-service\",\"_tenant\":\"$TENANT\",\"_workspace\":\"ws-1\"}")"
  MCP_STATUS_ACTION="$(printf '%s' "$mcp_status" | python3 -c 'import json,sys; print(json.load(sys.stdin)["action_id"])')"
  [ "$(wait_terminal_for "$MCP_STATUS_ACTION" "$AI_JWT")" = "succeeded" ] ||
    fail "AI/MCP diagnostics did not succeed"

  mcp_restart="$("$WORK/forgectl" mcp call --server http://127.0.0.1:18055 acme_service_restart \
    "{\"service\":\"acme-service\",\"_tenant\":\"$TENANT\",\"_workspace\":\"ws-1\"}")"
  MCP_RESTART_ACTION="$(printf '%s' "$mcp_restart" | python3 -c 'import json,sys; print(json.load(sys.stdin)["action_id"])')"
  for _ in $(seq 1 80); do
    [ "$(action_status_for "$MCP_RESTART_ACTION" "$AI_JWT")" = "held" ] && break
    sleep 0.5
  done
  [ "$(action_status_for "$MCP_RESTART_ACTION" "$AI_JWT")" = "held" ] ||
    fail "AI/MCP restart did not hold for customer approval"
  mcp_restarts_before="$(state_field restart_count)"
  MCP_PROP="$(proposal_for "$MCP_RESTART_ACTION")"
  [ -n "$MCP_PROP" ] || fail "no proposal for AI/MCP restart"

  # The claim this whole path exists to make is that the AI can ASK and cannot
  # DECIDE. Everything above proves the asking half: the AI'"'"'s restart holds and
  # its shell request is refused. Neither shows that the AI cannot simply
  # release its own hold -- and the run stayed green whichever way that went,
  # because the approval below uses the approver'"'"'s credential regardless.
  #
  # So the AI attempts the approval itself, with its own token, and must be
  # refused. The positive control is the approver'"'"'s decide() on the very next
  # line: same endpoint, same proposal, different identity, opposite outcome.
  # Without both halves in one fixture, "no approver role" is narration -- it
  # was recorded in the evidence file while nothing checked it.
  ai_decide_status="$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    "$PLATFORM/v1/tenants/$TENANT/proposals/$MCP_PROP/decide" \
    -H "Authorization: Bearer $AI_JWT" -H 'Content-Type: application/json' \
    -d '{"decision":"approve","note":"ai self-approval attempt"}')"
  case "$ai_decide_status" in
    401|403) ;;
    *) fail "the AI/MCP requester approved its own hold (HTTP $ai_decide_status); the requester and the authority are the same identity" ;;
  esac
  [ "$(action_status_for "$MCP_RESTART_ACTION" "$AI_JWT")" = "held" ] ||
    fail "the AI/MCP self-approval attempt moved the action out of held"
  [ "$(state_field restart_count)" = "$mcp_restarts_before" ] ||
    fail "the AI/MCP self-approval attempt reached the target"

  decide "$MCP_PROP" approve
  [ "$(wait_terminal_for "$MCP_RESTART_ACTION" "$AI_JWT")" = "succeeded" ] ||
    fail "approved AI/MCP restart did not succeed"
  mcp_restarts_after="$(state_field restart_count)"
  [ "$mcp_restarts_after" = "$((mcp_restarts_before + 1))" ] ||
    fail "AI/MCP restart_count $mcp_restarts_before -> $mcp_restarts_after, want one effect"

  mcp_shell="$("$WORK/forgectl" mcp call --server http://127.0.0.1:18055 acme_service_shell \
    "{\"service\":\"acme-service\",\"command\":\"whoami\",\"_tenant\":\"$TENANT\",\"_workspace\":\"ws-1\"}")"
  MCP_SHELL_ACTION="$(printf '%s' "$mcp_shell" | python3 -c 'import json,sys; print(json.load(sys.stdin)["action_id"])')"
  [ "$(wait_terminal_for "$MCP_SHELL_ACTION" "$AI_JWT")" = "failed" ] ||
    fail "AI/MCP shell action did not fail"
  mcp_shell_reason="$(request_json GET "$PLATFORM/v1/tenants/$TENANT/actions/$MCP_SHELL_ACTION/explain" "$AI_JWT" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("action") or {}).get("failure_reason",""))')"
  case "$mcp_shell_reason" in *"denied by edge policy"*) ;; *) fail "AI/MCP shell refusal was not policy denial: ${mcp_shell_reason:-<none>}" ;; esac
  [ "$(state_field restart_count)" = "$mcp_restarts_after" ] ||
    fail "AI/MCP shell denial changed target state"
  if grep -q "$CUSTOMER_TOKEN" "$WORK/forge-mcp.log" 2>/dev/null; then
    fail "customer token leaked into MCP adapter log"
  fi
  ok "AI/MCP diagnostics, governed restart and shell refusal used the same canonical path"

  cat > "$WORK/first-touch-ai-mcp.md" <<EOF
# ForgeOps first-touch AI/MCP proof (#556)

$(date -u '+%Y-%m-%d %H:%M UTC')

- requester: ai-caller (member/ws-1; no approver role)
- adapter: forge-mcp composed with the Platform Action Gateway
- diagnostics Action: $MCP_STATUS_ACTION succeeded
- restart Action: $MCP_RESTART_ACTION held, customer-approved, succeeded; restart_count $mcp_restarts_before -> $mcp_restarts_after
- shell Action: $MCP_SHELL_ACTION failed; $mcp_shell_reason; restart_count remained $mcp_restarts_after
- customer credential exposure to model/requester: none
- AI self-approval attempt on its own hold: refused (HTTP $ai_decide_status), action stayed held, zero target effect

The MCP adapter received only the workspace Action credential. It did not receive
the customer token, edge credential, approval signing key, SSH, VPN, or direct
target access. The AI/requester could ask; customer-side authority decided.
EOF
fi

cat > "$WORK/first-touch-run.md" <<EOF
# ForgeOps first-touch local run (#554)

$(date -u '+%Y-%m-%d %H:%M UTC')

## Revisions

- forgeops-control: $(repo_rev "$ROOT" "$CONTROL_REV")
- forgeops-platform: $(repo_rev "$PLATFORM_DIR" "$PLATFORM_REV")
- forgeops-capabilities: $(repo_rev "$CAPABILITIES_DIR" "$CAPABILITIES_REV")

## Outcomes

- diagnostics: $STATUS_ACTION succeeded; pending_jobs=$pending config=$config restart_count=$restarts_before
- restart approved: $RESTART_ACTION held, approved, succeeded; restart_count $restarts_before -> $restarts_after; receipt=$receipt
- restart denied: $REJECT_ACTION held, denied, $reject_status; restart_count remained $restarts_after
- shell access: $SHELL_ACTION failed; $shell_reason; restart_count remained $restarts_after

## Path

All requester operations were Platform Actions through Control, the outbound edge
session, the edge policy gate and packaged ACME runtimes. The approval page at
http://127.0.0.1:18054/ used Platform proposal APIs; it did not approve locally.
EOF

if [ -n "$FIRST_TOUCH_BIN_DIR" ]; then
  cat > "$WORK/first-touch-metrics.md" <<EOF
# ForgeOps first-touch friction measures (#555)

$(date -u '+%Y-%m-%d %H:%M UTC')

- evaluator bootstrap actions before ACME Ready: $COMMANDS_BEFORE_READY
- time from bootstrap start to ACME Ready: $((READY_EPOCH - START_EPOCH)) seconds
- undocumented interventions required: 0
- reset path: bash scripts/first-touch-reset.sh
- source clone/build required on evaluator path: no
- account/email/GitHub OAuth required before aha moment: no
- ACME Ready state: pending_jobs=$pending config=$config restart_count=$restarts_before

The run used prebuilt local bundle binaries from $FIRST_TOUCH_BIN_DIR.
EOF
else
  cat > "$WORK/first-touch-metrics.md" <<EOF
# ForgeOps first-touch maintainer-run friction measures (#555)

$(date -u '+%Y-%m-%d %H:%M UTC')

- bootstrap actions before ACME Ready: $COMMANDS_BEFORE_READY
- time from script start to ACME Ready: $((READY_EPOCH - START_EPOCH)) seconds
- undocumented interventions required: 0
- reset path: bash scripts/first-touch-reset.sh
- source clone/build required on this maintainer path: yes
- account/email/GitHub OAuth required before aha moment: no
- ACME Ready state: pending_jobs=$pending config=$config restart_count=$restarts_before
EOF
fi

echo
printf '\033[1;32mFIRST-TOUCH PASSED\033[0m — evidence in %s\n' "$WORK/first-touch-run.md"
printf 'friction measures in %s\n' "$WORK/first-touch-metrics.md"
