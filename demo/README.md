# Run the demo

No account, no email, no form. Download it and run it.

## Download

Pick your platform:

| | |
|---|---|
| macOS, Apple silicon | `forgeops-first-touch-darwin-arm64.tar.gz` |
| macOS, Intel | `forgeops-first-touch-darwin-amd64.tar.gz` |
| Linux, x86-64 | `forgeops-first-touch-linux-amd64.tar.gz` |
| Linux, arm64 | `forgeops-first-touch-linux-arm64.tar.gz` |

```bash
BASE=https://eu2.contabostorage.com/d89295baa09047ca80427839e7799618:forgeops/first-touch/6924153696ef
KIT=forgeops-first-touch-darwin-arm64.tar.gz    # change to match your platform

curl -O "$BASE/$KIT"
curl -O "$BASE/$KIT.sha256"
shasum -a 256 -c "$KIT.sha256"

tar -xzf "$KIT"
cd forgeops-first-touch-*
./try-forgeops
```

Downloading in the terminal is not incidental. The binaries are not code-signed
— we have not bought into Apple's signing programme — and macOS attaches a
quarantine flag to anything a browser downloads, which would block them. `curl`
does not set that flag, so nothing is being bypassed or overridden; the demo
simply runs.

Check the checksum anyway. It is the only integrity claim we can make right
now, and it is worth more than our assurance.

The path carries a build identifier, so a link always means exactly one build.
Published artifacts are never overwritten — if you come back to this URL later
you get the same bytes, and a newer build lives at a different one.

## What you will see

Three requests against a fictional customer connector running on your machine:

```text
read diagnostics       ALLOW   runs immediately, returns the connector's state
restart the connector  ASK     waits for a human, then really restarts it
open a shell           DENY    refused, and the connector is untouched
```

That is the whole demo. The interesting part is not that the restart works —
it is that the shell request cannot be made to work, and that the restart
needed someone else's decision.

## What is actually running

Everything is on your laptop, but it is arranged as three separate sides that
only talk through ForgeOps. No process reaches across a line.

```text
  YOUR LAPTOP
  ..........................................................................
  :                                                                        :
  :  VENDOR SIDE            you, asking for something                      :
  :    forgectl             the requester CLI                              :
  :    forge-mcp            the same requests, made by an AI                :
  :                              |                                         :
  :                              |  "restart acme-service"                 :
  : - - - - - - - - - - - - - - -|- - - - - - - - - - - - - - - - - - - -  :
  :                              v                                         :
  :  FORGEOPS                the managed side. sees requests, never the     :
  :    api                   customer's credentials or machine             :
  :    forge-control         records the Action, decides placement, relays  :
  :                              |                                         :
  :                              |  outbound session, opened by the edge    :
  : - - - - - - - - - - - - - - -|- - - - - - - - - - - - - - - - - - - -  :
  :                              v                                         :
  :  CUSTOMER SIDE           the environment you are NOT given access to    :
  :    forge-agent           the edge. holds the policy and the secret      :
  :    approval page :18054  where a human allows or refuses                :
  :                              |                                         :
  :                              v                                         :
  :    acme-service-status   capability: read state                        :
  :    acme-service-restart  capability: restart, once, with a receipt     :
  :                              |                                         :
  :                              v                                         :
  :    acme-service          THE TARGET. the fictional connector, with      :
  :                          real state you can read                       :
  ..........................................................................
```

Which binary is what:

| binary | side | what it is |
|---|---|---|
| `forgectl` | vendor | the requester. asks for one named operation |
| `forge-mcp` | vendor | an AI making the same requests, same path |
| `api` | ForgeOps | records the Action and the approval decision |
| `forge-control` | ForgeOps | places the request on an edge, relays the result |
| `forge-agent` | customer | the edge. syncs policy, runs capabilities, holds the secret |
| `acme-service-status` | customer | capability: reads the connector's state |
| `acme-service-restart` | customer | capability: restarts it, exactly once |
| `acme-service` | customer | the target being operated on |

The direction of the arrow between ForgeOps and the edge matters: **the edge
opens the connection outward**. Nothing dials into the customer side, which is
why this works where a VPN or an inbound agent would not be allowed.

## When each thing happens

**Diagnostics — allowed, so nobody is asked.**

```text
forgectl ---> api ---> forge-control ---> forge-agent
                                              |
                                     policy says: allow
                                              |
                                              v
                                   acme-service-status
                                              |
                                              v
                              pending_jobs=17 config=v4
```

**Restart — held, until a person on the customer side decides.**

```text
forgectl ---> api ---> forge-control ---> forge-agent
                                              |
                                     policy says: ask
                                              |
                          the action stops here. nothing runs.
                                              |
                          you open http://127.0.0.1:18054/
                          and approve AS THE CUSTOMER, not as the requester
                                              |
                                              v
                                   acme-service-restart
                                              |
                                              v
                                  restart_count 0 -> 1
                                  receipt names the action
```

Run it again and refuse: the count stays where it is. Nothing reached the
target, because the decision — not the request — is what releases the effect.

**Shell — denied by policy, and there is nothing to negotiate with.**

```text
forgectl ---> api ---> forge-control ---> forge-agent
                                              |
                                policy rule 3: deny
                                              |
                                     refused. nothing runs.
                                     restart_count unchanged
```

The refusal is an outcome, not an error. And it does not depend on the
requester behaving: there is no input to the allowed operations that turns one
of them into a shell.

## Where the credential lives

The connector needs a token to be restarted. That token is written into the
edge's secrets file and passed to the capability by the edge, on the customer
side. It is never sent to the requester, and the run fails if it turns up
anywhere it should not.

That is the point of the whole arrangement: you caused a restart inside an
environment you were never given access to.

## What is in it

```text
bin/          the ForgeOps runtime and the fictional ACME connector
scripts/      what the entry points run, readable before you run them
docs/         the same concepts as this repository, offline
try-forgeops  the entry point
SHA256SUMS    checksums for everything above
```

Nothing in the bundle phones home, and nothing needs network access except
pulling the Postgres image the first time.

## Try it with an AI requester

```bash
./try-with-ai-mcp
```

The same three requests, made by `forge-mcp` instead of a person. Same Actions,
same policy, same approval. The model receives a workspace credential and
nothing else — it cannot approve its own request, and the run checks that by
having it try.

## Start over

```bash
bash scripts/first-touch-reset.sh
```
