# Bring your own operation

The demo's four capabilities are not special. `--with` takes a directory, and
what is in it runs as one more phase of Demo 1 — through the same Action,
placement, edge policy gate and evidence path as the built-in operations.

```bash
./try-forgeops --with ./my-capability
```

## What it proves

Your binary is executed **by the customer-side edge**, not by the harness. The
edge admits it against local policy, hands it a scoped runtime token the
requester never sees, and reports its receipt through the same ledger. From a
real run's `with-capability.log`:

```text
sdk: run=rdlf34c8cadxp input=26B runtime_url="http://127.0.0.1:8011" token=true
```

That `token=true` is the claim: the edge gave *your* runtime a credential it
never gave the requester that asked for the operation.

## The directory needs two things

| | |
|---|---|
| `capability.yaml` | the manifest — what the operation is and what authority it asks for |
| one executable beside it | your runtime, serving two HTTP endpoints |

Nothing else. The harness finds the executable with
`find -maxdepth 1 -type f -perm -111`, so keep exactly one there.

## The manifest

```yaml
name: inventory.refresh          # the capability uid
revision: 1
description: Refresh one bounded slice of inventory state.

input:
  service: string

effect:
  mutation: true                 # does this change the customer's system?

targets:
  - kind: service
    names: [acme-service]        # the FIRST name here is what it acts on
```

**The manifest decides the policy, not the code.** The harness derives the edge
policy binding from it:

| manifest says | binding | why |
|---|---|---|
| `effect.mutation: true`, no `decision:` | `ask` | something that changes a customer's system asks |
| `effect.mutation: false`, or no effect block | `allow` | a read runs without a human |
| `decision: allow` \| `ask` \| `deny` | exactly that | an explicit decision wins |

`decision:` must be at the **top level — column 0**, not nested under `effect:`.
Indented, it is refused with a message telling you to move it; in kits built
before that guard, it was silently ignored and the derived default applied
instead.

## The runtime contract

Two endpoints on `CAPABILITY_ADDR` (`:8099` by default, or
`FIRST_TOUCH_WITH_PORT`):

**`GET /health`** → `200`, no body required.

**`POST /run`** receives:

```json
{
  "run_id":        "rdlf34c8cadxp",
  "input":         {"service": "acme-service"},
  "runtime_token": "<scoped token for callbacks>",
  "runtime_url":   "http://127.0.0.1:8011",
  "deadline":      "2026-09-14T15:48:29Z",
  "context":       {"action_id": "...", "idempotency_key": "...", "attempt_number": 1}
}
```

`deadline` and `context` are present when the executor sends them. `context`
carries the canonical action identity your receipt should name.

**Success** is `200` with your result as the body — no envelope:

```json
{"service": "acme-service", "refreshed": true, "refresh_count": 1, "receipt": "..."}
```

**Failure** is a classed error, and the class chooses the status:

```json
{"error": "service \"billing-service\" is not a declared target on this deployment",
 "error_class": "refused"}
```

| `error_class` | status | means |
|---|---|---|
| `invalid_input` | 400 | the input did not match what you declared |
| `refused` | 409 | asked to act outside what this deployment gave you |
| `denied` | 409 | the capability refuses by declaration |
| `invalid_output` | 500 | output did not match the declared schema |
| `timeout` | 500 | the run exceeded its deadline |
| `internal` | 500 | a fault |

The refusal classes are deliberately **not 5xx**: a capability enforcing a
boundary is not a fault, and reporting it as one makes authority being enforced
indistinguishable from a crash — in logs, in metrics, and to a retry policy that
treats 5xx as transient.

Any language that can serve those two endpoints can implement a capability. The
Go SDK is a convenience that handles the envelopes, the deadline and the
refusal classes for you; it is a source bundle available on request rather than
a published module — see [CONTACT.md](../CONTACT.md).

## Build it

Copy the worked example, point a `replace` at the SDK bundle, build:

```bash
cp -R examples/inventory-check ./my-capability
cd my-capability

cat > go.mod <<'MOD'
module example.com/my-capability

go 1.23

require github.com/ykdynamics/forgeops-capabilities v0.0.0

replace github.com/ykdynamics/forgeops-capabilities => ../forgeops-capability-sdk-<version>
MOD

go build -o my-capability .
```

## Run it

```bash
bash scripts/first-touch-reset.sh
./try-forgeops --with ./my-capability
```

Your operation arrives as the last phase:

```text
== Z. inventory.refresh — an operation you wrote, through the same path ==
OK: inventory.refresh succeeded through Platform, Control, the edge policy gate and your runtime
```

**Phase Z is last, so the phases before it have to pass.** Two of them stop for
a browser decision, and they want *different* answers — the terminal names which:

| phase | the prompt says | do this |
|---|---|---|
| B/C | `…and approve proposal prop-…` | **approve** |
| D | `…and reject proposal prop-…` | **reject** |

Approving the second one fails the run (`denied restart did not reach a terminal
refusal`) three phases before your capability gets a turn — it will have been
loaded and hosted, but never invoked. To skip the decisions entirely:

```bash
AUTO_DECIDE=1 ./try-forgeops --with ./my-capability
```

## Verify it actually ran

```bash
grep 'sdk: run=' /tmp/forgeops-first-touch-kit.*/with-capability.log
```

A `sdk: run=` line is the proof your code executed inside the demo. No line
means phase Z was never reached — check whether an earlier phase failed.

## The pair worth running

Comment out `decision: allow` and run the **identical binary** again:

```bash
sed -i 's/^decision: allow/# decision: allow/' my-capability/capability.yaml
bash scripts/first-touch-reset.sh
./try-forgeops --with ./my-capability
```

Phase Z now holds and prints its own approval prompt. Same code, byte for byte;
opposite authority. That pair is the whole claim: the boundary is carried by the
declaration, and it is the customer's policy — not your implementation — that
decides whether a human is involved.

## When it will not start

| message | cause |
|---|---|
| `has no executable beside capability.yaml` | you pointed at the source template, not a built directory |
| `declares no name:` | `name:` must be at the top level |
| `has an indented 'decision:'` | move it to column 0, outside the effect block |
| `decision must be allow, ask or deny` | typo in an explicit decision |

---

Next: [what the local demo does and does not prove](../docs/concepts/what-this-proves.md).
