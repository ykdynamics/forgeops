# ForgeOps First Touch

**Operate software inside customer environments -- without remote access.**

Diagnose, restart, or repair software running behind a customer boundary.
ForgeOps lets you request specific operations without receiving SSH, VPN,
credentials, or general access to the environment.

## Try It On This Machine

Prerequisites:

- Docker running locally
- `curl`, `python3`, `lsof`, and `bash`
- ports `8010`, `8011`, `8012`, `8080`, `8089`, `8093`, `8094`, `8095`,
  `18054`, `18055`, `18056`, `18057`, and `55454` free

One action:

```bash
./try-forgeops
```

What you will see, in order:

1. the local ACME customer connector becomes Ready;
2. diagnostics read real connector state;
3. restart is held until customer approval in the browser;
4. the local connector restart count changes;
5. shell access is refused with no local effect;
6. the run writes friction measures and evidence under `/tmp`.

## Inspect Or Manual Install

The bundle is intentionally plain files. Before running it you can inspect:

```bash
find . -maxdepth 3 -type f | sort
shasum -a 256 -c SHA256SUMS        # covers every file listed above
sed -n '1,220p' try-forgeops
```

`pwa/` is the ForgeOps Approval PWA, built. It is the surface you decide in, and
it is the same one used elsewhere rather than a page written for this demo.

There is no `curl | sh` requirement. You may unpack the archive, inspect every
script, then run `./try-forgeops`.

## Try It With A Real Model

After the basic journey makes sense:

```bash
./try-with-ai
```

A real model sits in the requester seat. It reads the connector, works out what
is wrong, and asks for an operation; policy and a person on your side decide what
happens to the request. The connector is seeded with one of four faults and the
right operation differs per run, so there is something to work out rather than
one button to press.

The approval happens in the real ForgeOps Approval PWA. The terminal prints a
link carrying a one-time session for a `customer-approver` identity, distinct
from the model's, and the page strips it from the address bar as soon as it
loads. That identity is a real credential with the approver role: the server
validates it, derives the approver from it, and refuses a decision from anything
without the role. What this demo skips is the sign-in ceremony, not the
authentication.

You need no account and no API key. The model runs on our side, behind a metered
relay. What leaves your machine is what you type and what the demo's own
connector reports -- nothing else on it is read, and the model never receives a
credential, a shell, or a route to anything.

If you would rather nothing left this machine for ours, point it at your own
endpoint instead. The demo is identical:

```bash
FORGE_MODEL_ENDPOINT=https://api.anthropic.com ANTHROPIC_API_KEY=sk-... ./try-with-ai
```

Things worth trying: ask it to open a shell, ask it to export the data, tell it
to approve its own restart. The request is always allowed to be made; what
refuses it is the part worth watching. And the policy the edge enforces is a
file on your disk -- the page tells you where -- so a refusal you disagree with
is one you can move.

## The Scripted Path

```bash
./try-with-ai-mcp
```

The same journey driven by a script instead of a model, with approvals
automatic. Useful to read rather than run: it shows the exact calls, and it is
what `./try-with-ai` replaced.

## Reading

The explanation lives with the download, where it is written for you and stays
current:

- what just happened, and who decided what
- why this is not remote access with extra steps
- what this demo does and does not prove -- read that one

  https://github.com/ykdynamics/forgeops

## Reset And Retry

```bash
bash scripts/first-touch-reset.sh
./try-forgeops
```

To also remove retained `/tmp` evidence directories:

```bash
FIRST_TOUCH_PURGE=1 bash scripts/first-touch-reset.sh
```
