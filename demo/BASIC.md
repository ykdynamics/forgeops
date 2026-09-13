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
KIT=forgeops-first-touch-darwin-arm64.tar.gz    # change to match your platform

curl -O "$BASE/$KIT"
curl -O "$BASE/$KIT.sha256"
shasum -a 256 -c "$KIT.sha256"

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

## Next: change the requester to AI

Once the authority model is clear, run **Demo 2 — AI + MCP**:

```bash
./try-with-ai
```

[Continue to Demo 2 →](AI.md)

## Start over

```bash
bash scripts/first-touch-reset.sh
```
