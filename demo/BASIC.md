# Demo 1 — Core authority

**See the ForgeOps trust model first: ALLOW, ASK and DENY against a real local target.**

```bash
./try-forgeops
```

| | |
|---|---|
| Time | about 2 minutes |
| Runs | locally on your machine |
| Account | none |
| Requires | Docker, `curl`, `python3`, `lsof`, `bash` |
| Network | Postgres image download on first run; no ForgeOps service is contacted |
| Cleanup | `bash scripts/first-touch-reset.sh` |

The customer system is synthetic. The operations are not. Diagnostics read the
connector's real state, approval really gates the restart, and a denied request
produces no target effect.

## What you will see

Three requests go through the same authority path:

![The demo sends three requests through customer policy: diagnostics are allowed, restart asks for customer approval, and shell access is denied with no target effect.](../docs/images/demo-allow-ask-deny.svg)

```text
read diagnostics       ALLOW   runs immediately, returns connector state
restart the connector  ASK     stops until the customer decides
open a shell           DENY    refused; the connector is untouched
```

The interesting part is not that the restart works. It is that the requester
cannot make the shell work, and cannot release the held restart by itself.

## What opens in your browser

When the restart reaches `ASK`, the terminal prints a localhost link to the
**ForgeOps Approval PWA**. The page shows the exact requester, purpose,
operation and target being decided.

This checked-in preview shows the information you should expect to see; the demo
opens the real browser surface.

![Preview of the customer approval surface: one requester, one purpose, one exact operation and target, with approve or deny.](../docs/images/customer-approval.svg)

Approve once and the connector's `restart_count` moves from `0` to `1`. Run the
held case again and deny it: the counter stays where it is.

## Before you download

```text
Docker           running (the demo starts a Postgres container)
curl, python3, lsof, bash
ports free       8010-8012, 8080, 8089, 8093-8095, 18054-18057, 55454
                 plus 8099 if you use --with
about 1 GB       the kit plus the Postgres image on first run
```

Every demo port binds to localhost. Nothing opens an inbound route to your
machine.

## Download

Pick your platform:

| Platform | Bundle |
|---|---|
| macOS, Apple silicon | `forgeops-first-touch-darwin-arm64.tar.gz` |
| macOS, Intel | `forgeops-first-touch-darwin-amd64.tar.gz` |
| Linux, x86-64 | `forgeops-first-touch-linux-amd64.tar.gz` |
| Linux, arm64 | `forgeops-first-touch-linux-arm64.tar.gz` |

```bash
BASE=https://eu2.contabostorage.com/d89295baa09047ca80427839e7799618:forgeops/first-touch/d5c50a10e10f
KIT="forgeops-first-touch-$(uname -s | tr 'A-Z' 'a-z')-$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz"

curl -O "$BASE/$KIT"
curl -O "$BASE/$KIT.sha256"
shasum -a 256 -c "$KIT.sha256" 2>/dev/null || sha256sum -c "$KIT.sha256"

tar --exclude='._*' -xzf "$KIT"
cd "$(tar -tzf "$KIT" 2>/dev/null | cut -d/ -f1 | grep -v '^\._' | head -1)"
./try-forgeops
```

The binaries are not code-signed. On macOS, downloading with `curl` avoids the
browser quarantine flag that would otherwise stop an unsigned binary from
starting. Check the SHA-256 file anyway: it is the integrity claim available for
this early preview.

The artifact path includes a build identifier. Published builds are not
overwritten.

If you are testing on Linux, see the [Linux quick start](LINUX.md).

## The run, in one screen

A normal run looks roughly like this:

```text
== starting Postgres, Platform and Control ==
OK: Platform and Control ready

== starting ACME Sync Connector, capability runtimes and edge ==
OK: first-touch-edge Ready

== diagnostics ALLOW ==
OK: pending_jobs=17 config=v4 restart_count=0

== restart ASK ==
Open http://127.0.0.1:18057/#ft=... and approve proposal ...
OK: restart approved and executed exactly once

== deny a held restart ==
Open the approval page and reject proposal ...
OK: denied restart produced zero target effect

== shell DENY ==
OK: shell refused by customer policy; target unchanged

FIRST-TOUCH PASSED
```

The demo stops for approval because the Action has reached the customer side and
cannot continue without another identity making the decision.

## What is actually running

Everything is on one laptop for first touch, but the logical sides stay
separate:

![The local demo has vendor, ForgeOps and customer-side components; policy, credential and target remain on the customer side, and the edge opens its session outward.](../docs/images/demo-three-sides.svg)

| Binary | Side | Purpose |
|---|---|---|
| `forgectl` | requester/operator | drives the fixed first-touch scenario |
| `forge-mcp` | requester | exposes the same capabilities to MCP callers |
| `api` | ForgeOps | records the canonical Action and proposal state |
| `forge-control` | ForgeOps | places the Action and relays the result |
| `forge-agent` | customer | enforces policy and owns the local credential path |
| `acme-service-status` | customer | reads target state |
| `acme-service-restart` | customer | performs one bounded restart |
| `acme-service` | customer | fictional target with observable real state |

The edge opens the session outward. Nothing dials into the customer side.

## What actually happens, in order

The component view above is where things sit. This is the order they move in,
for the restart — the one operation that stops.

```mermaid
sequenceDiagram
    autonumber
    actor R as Requester (vendor)
    participant P as Platform (api)
    participant C as Control (forge-control)
    participant E as Edge (forge-agent)
    participant K as Capability runtime
    participant T as acme-service (target)
    actor A as Approver (customer)

    Note over E,C: the edge already holds an outbound session —<br/>nothing ever dials into the customer side

    R->>P: Action: acme.service.restart rev 1, target acme-service,<br/>input, policy_revision, purpose
    P->>P: record canonical Action act-… and hash the input
    P->>C: place the Action
    C-->>E: delivered down the edge's own session

    E->>E: local policy: restart = ask
    E-->>P: held, proposal prop-…

    P-->>A: shown in the Approval PWA<br/>requester, purpose, operation, target
    A->>P: approve prop-…
    P->>P: sign the grant (audience forgeops-edge, short ttl)
    P->>C: grant
    C-->>E: grant

    E->>E: verify the signature against approval-trust.pem,<br/>then check the target and input hash match what was approved
    E->>K: execute, with SERVICE_TOKEN from the edge's own secrets
    K->>T: restart, once
    T-->>K: restart_count 0 → 1, receipt
    K-->>E: receipt
    E-->>P: succeeded, with the receipt
    P-->>R: succeeded
```

Two things in that order matter more than the rest.

**Step 4 is a delivery, not a connection.** Control does not reach into the
customer side; it hands the Action to a session the edge opened outward. You can
watch that session come up in the edge's own log, `agent.log` in the run's work
directory under `/tmp/forgeops-first-touch-kit.*`:

```text
agent: first-touch-edge maintains an outbound session at 127.0.0.1:8012
agent: first-touch-edge session live at 127.0.0.1:8012
```

**Step 12 is where an approval becomes an effect, and it is checked twice.** The
edge verifies who signed the grant, then verifies that the operation and target
in it are the ones the approver was shown. Only then does it supply the
credential (13) and let the restart happen, once (14). A grant for a different
target does not execute — approving one thing cannot release another.

### Where the three outcomes diverge

All three requests take the same path to the edge. They separate at one point:

```mermaid
flowchart LR
    A["Action arrives<br/>at the edge"] --> P{"local policy<br/>for this capability"}
    P -->|"allow<br/>diagnostics"| X["execute now"]
    P -->|"ask<br/>restart"| H["hold for a<br/>separate approver"]
    P -->|"deny<br/>shell"| N["refuse<br/>no target effect"]
    H -->|approved| X
    H -->|denied| N
```

The decision is the customer's policy, evaluated on the customer's side, after
the Action has already arrived. That is why the refusal is not a missing feature
on the vendor side — the request was made, reached the edge, and was stopped
there.

### The run, phase by phase

Each banner in the terminal maps to one of those layers doing one thing:

| Banner | What is happening |
|---|---|
| `using the bundled ForgeOps runtime` | prebuilt binaries from the kit; nothing is compiled |
| `preparing local ports` | frees the fixed loopback ports the demo uses |
| `starting Postgres, Platform and Control` | the ForgeOps side comes up; canonical-input enforcement on |
| `declaring the first-touch fabric` | applies Environment, four Capabilities, Agent, Policy — 7 resources |
| `starting ACME Sync Connector, capability runtimes and edge` | the customer side comes up and the edge reaches `Ready` |
| `provisioning requester and customer-approver identities` | two distinct subjects; the requester cannot approve |
| `A. diagnostics ALLOW` | policy allows, no human, target state returned |
| `B/C. restart ASK` | held at the edge until the PWA decision, then one real effect |
| `D. denying a held restart` | same path, opposite decision, `restart_count` unchanged |
| `shell DENY` | refused by policy; never reaches the target |

The fabric and identity phases are the ones worth not skipping. The policy that
stops the restart is applied in the fourth phase, from a file, and the identity
that can approve it is created in the sixth — separately from the one that asks.

## How a requester asks

The demo is driven for you, but the product contract is an Action. A normal
request binds the exact operation, revision, target, input and policy context
before placement:

```http
POST /v1/tenants/{tenant}/actions
Authorization: Bearer <workspace token>

{
  "workspace_id":        "ws-1",
  "capability_uid":      "acme.service.restart",
  "capability_revision": 1,
  "target":              "acme-service",
  "input":               {"service": "acme-service"},
  "policy_revision":     1,
  "idempotency_key":     "restart-after-queue-alert",
  "max_attempts":        1,
  "request_purpose":     "Connector has 17 pending jobs."
}
```

`capability_revision` pins which operation was requested. `request_purpose` is
what the customer reads when the Action needs approval.

The AI/MCP demo uses the same Action path. `forge-mcp` is an adapter in front of
it, not a second execution route.

## Where the credential lives

The fictional connector requires a token for restart. The edge keeps that token
on the customer side and supplies it only to the bounded capability. The
requester never receives it.

That is the point of the arrangement: the requester causes one authorized
effect without being given general access to the environment.

## Inspect it further

```bash
forgectl pending          # held calls
forgectl approvals        # proposal ledger
forgectl audit --tail 20  # request / decision / execution record
forgectl edges            # edge status
forgectl doctor           # boundary-oriented diagnostics
```

For the diagram-first explanation, see the [visual walkthrough](VISUAL-GUIDE.md).
For exact claim boundaries, see [what the local demo does and does not prove](../docs/concepts/what-this-proves.md).

## Send an operation of your own through it

The demo's four capabilities are not special. `--with` takes a directory and
runs what is in it as one more phase — **Z**, after the built-in ALLOW, ASK and
DENY — through the same Action, placement and customer-side policy path.

```bash
./try-forgeops --with ./my-capability
```

The directory needs exactly two things:

| | |
|---|---|
| `capability.yaml` | the manifest: a `name:`, a `targets:` block whose first `names: [...]` entry is what it acts on, and an effect |
| one executable beside it | your runtime, started with `CAPABILITY_ADDR` and serving `GET /health` and `POST /run` |

**The manifest decides the policy, not the code.** Declare `effect.mutation:
true` and leave the decision out, and the harness binds your operation to `ask`:

```yaml
effect:
  mutation: true
```

Run it and your own operation holds, waiting for the same separate approver in
the same PWA. Add `decision: allow` to the manifest and run the identical binary
again — the hold is gone. That is the whole claim in one edit: something that
changes a customer's system asks, unless someone decided otherwise on purpose,
and the deciding happens in a declaration rather than in your implementation.

A read (`mutation: false`, or no effect block) defaults to `allow` and runs
without a human, exactly as diagnostics does.

[The worked example](../examples/) has a manifest and an implementation to copy.
The SDK it builds against is a source bundle available on request rather than a
published module — see [CONTACT.md](../CONTACT.md) — but it is a convenience,
not the contract: the harness requires an executable serving two HTTP
endpoints, so an operation can be written in anything.

**[The full walkthrough →](BRING-YOUR-OWN.md)** — the manifest contract, both
endpoints with their payloads and error classes, the approval sequence phase Z
sits behind, and how to verify the edge really ran your code.

## Next: change the requester to AI

Once the authority model is clear, run **Demo 2 — AI + MCP**:

```bash
./try-with-ai
```

[Continue to Demo 2 →](AI.md)

## If it does not start

Four failures account for nearly every unsuccessful first run.

**`platform exited before it became usable (pid …)`** — two different causes,
one message.

First check the bundle matches your machine:

```bash
file bin/api        # must say your platform, e.g. "ELF 64-bit ... x86-64" on Linux
```

`Mach-O` on Linux (or the reverse) means the wrong bundle was downloaded — the
command above picks it automatically, so re-run the download block.

If the bundle is right, **run it again.** Bundles built before 14 September 2026
check whether Postgres is ready over a Unix socket, which reports success a
fraction of a second before the database accepts TCP connections. It fails
roughly one run in four and succeeds on a retry. Later bundles wait for the
right thing.

**`cannot start: port :NNNN is already listening`** — something from a previous
run survived, or another program holds the port:

```bash
bash scripts/first-touch-reset.sh
```

**`cd: not a directory: ._forgeops-first-touch-…`** — the bundle was packaged on
macOS with a sidecar file per entry, and `._…` sorts first. The extract command
in the download block above skips them; bundles built after 13 September 2026 do
not contain them.

**`FIRST-TOUCH FAILED: denied restart did not reach a terminal refusal`** — the
run asks for two browser decisions and they want different answers. Phase B/C
says *approve*, phase D says *reject*. Approving both fails the run. Use
`AUTO_DECIDE=1 ./try-forgeops` to have both decided correctly for you.

For an empty approval page, see
[if the approval page is empty](AI.md#if-the-approval-page-is-empty) — the same
one-time session applies to both demos.

## Start over

```bash
bash scripts/first-touch-reset.sh
```
