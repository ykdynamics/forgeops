# lib-demo.sh — shared helpers for the demo scripts.
#
# The CI demos intentionally use fixed loopback ports so the evidence is easy to
# read and reproduce. On a persistent shared runner that is only safe if each
# demo proves the ports are free before it starts and proves its own launched
# process becomes the listener before any client command runs.
demo_assert_ports_free() {
  local name="$1" port owner
  shift
  for port in "$@"; do
    if command -v lsof >/dev/null 2>&1; then
      owner="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
      if [ -n "$owner" ]; then
        echo "$name cannot start: port :$port is already listening" >&2
        echo "$owner" >&2
        return 1
      fi
    elif (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then
      echo "$name cannot start: port :$port is already accepting connections" >&2
      return 1
    fi
  done
}

demo_start_process() {
  local pid_var="$1" name="$2" log_file="$3"
  shift 3
  local ports=()
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
    ports+=("$1")
    shift
  done
  if [ "$#" -eq 0 ]; then
    echo "demo_start_process: missing -- before command for $name" >&2
    return 1
  fi
  shift

  demo_assert_ports_free "$name" "${ports[@]}"
  "$@" >"$log_file" 2>&1 &
  local pid="$!"
  printf -v "$pid_var" '%s' "$pid"
  demo_assert_process_alive "$name" "$pid" "$log_file"
}

demo_assert_process_alive() {
  local name="$1" pid="$2" log_file="$3"
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$name exited before it became usable (pid $pid)" >&2
    tail -80 "$log_file" 2>/dev/null >&2 || true
    return 1
  fi
}

demo_wait_http_ready() {
  local name="$1" pid="$2" url="$3" log_file="$4" i
  shift 4
  for i in $(seq 1 50); do
    demo_assert_process_alive "$name" "$pid" "$log_file"
    if curl -fsS "$@" "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done
  echo "$name did not become ready at $url in time" >&2
  tail -80 "$log_file" 2>/dev/null >&2 || true
  return 1
}

# wait_agent_ready polls the fleet table until the named edge reports Ready.
# WP-04D placement only routes to a Ready, converged edge, so a fixed sleep
# after starting the agent is fragile on slow machines (CI): this is the
# guarantee that the demo's calls are routed at all.
wait_agent_ready() {
  local name="$1" pid="${2:-}" log_file="${3:-}" i
  for i in $(seq 1 40); do
    if [ -n "$pid" ] && [ -n "$log_file" ]; then
      demo_assert_process_alive "forge-agent $name" "$pid" "$log_file"
    fi
    if ./forgectl get agents 2>/dev/null | grep -Eq "${name}.*Ready"; then
      return 0
    fi
    sleep 0.5
  done
  echo "edge ${name} did not become Ready in time" >&2
  ./forgectl get agents >&2 || true
  return 1
}

# demo_failure_diagnostics dumps the state a failing demo needs to be
# diagnosed, and is meant to run from an ERR trap (control#507).
#
# The demo is the most integrated evidence CI produces — the part `make check`
# cannot cover — so a flaky demo makes the strongest evidence the least
# trustworthy. When one failed during R6.7 the only record was "denied by edge
# policy: rule 3", which does not say whether the policy was wrong, stale,
# still converging, or correctly refusing something the script did not expect.
# Re-running to green then destroyed the log entirely, so even that was lost.
#
# This prints, at the moment of failure:
#   - which command failed, and where;
#   - the fleet view: is the edge Ready, and what does it report?
#   - desired vs observed convergence: the policy revision the control plane
#     wants, and the one the edge has actually applied;
#   - the effective policy, so "rule 3" can be read as a rule rather than an
#     index;
#   - the tail of the agent and control logs.
#
# Everything is best-effort: a diagnostic that fails must not replace the
# original failure with its own.
demo_failure_diagnostics() {
  local exit_code="$1" line="${2:-?}" cmd="${3:-?}"
  {
    printf '\n\033[1;31m== DEMO FAILED (exit %s) ==\033[0m\n' "$exit_code"
    printf 'failing command: %s\n' "$cmd"
    printf 'script line: %s\n\n' "$line"

    printf -- '--- fleet (is the edge Ready?) ---\n'
    ./forgectl get agents 2>&1 || printf '(forgectl get agents failed)\n'

    printf -- '\n--- desired vs observed convergence ---\n'
    ./forgectl get agents -o json 2>/dev/null |
      grep -E '"(name|phase|policyRevision|appliedGeneration|appliedCaps)"' ||
      printf '(no structured agent status available)\n'

    printf -- '\n--- effective policy (so a rule INDEX can be read as a rule) ---\n'
    ./forgectl get policies -o json 2>&1 | head -60 ||
      printf '(forgectl get policies failed)\n'

    printf -- '\n--- forge-agent log (tail) ---\n'
    tail -40 /tmp/forge-agent.log 2>/dev/null || printf '(no agent log)\n'

    printf -- '\n--- forge-control log (tail) ---\n'
    tail -40 /tmp/forge-control.log 2>/dev/null || printf '(no control log)\n'

    printf -- '\n--- forge-automation log (tail) ---\n'
    tail -20 /tmp/forge-automation.log 2>/dev/null || printf '(no automation log)\n'
  } >&2
}
