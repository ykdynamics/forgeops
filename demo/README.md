# ForgeOps demos

Two demos. Same authority model.

If you are new to ForgeOps, start with Demo 1. Demo 2 changes the requester to a
real model after the trust boundary is already clear.

| | **Demo 1 — Core authority** | **Demo 2 — AI + MCP** |
|---|---|---|
| Purpose | Understand ForgeOps itself | See what changes when the requester is AI |
| Requester | fixed first-touch scenario | real model using MCP tools |
| Flow | diagnostics `ALLOW` → restart `ASK` → shell `DENY` | diagnose → reason → request → approval/refusal → verify |
| Customer authority | policy + separate approval | the same policy + separate approval |
| Runs | locally | locally; model context goes to the configured model endpoint |
| Account | none | none on the default hosted-model path |
| Start | `./try-forgeops` | `./try-with-ai` |
| Walkthrough | **[Run Demo 1 →](BASIC.md)** | **[Run Demo 2 →](AI.md)** |

## Demo 1 — Core authority

**See ALLOW, ASK and DENY produce real outcomes against a fictional connector on
your machine.**

```bash
./try-forgeops
```

Diagnostics run immediately. Restart reaches the customer side and stops until a
separate approver decides. Shell access is refused with zero target effect.

![Diagnostics are allowed, restart waits for customer approval, and shell access is denied.](../docs/images/demo-allow-ask-deny.svg)

**[Download and run Demo 1 →](BASIC.md)**

## Demo 2 — AI + MCP

**Put a real model in the requester seat without giving it customer authority.**

```bash
./try-with-ai
```

The model reads symptoms, chooses whether restart, resync, waiting or no action
makes sense, and requests bounded operations through `forge-mcp`. A consequential
operation still stops at `ASK`; the model cannot approve itself or widen policy.

![A real model diagnoses a connector and requests one bounded operation through the same ForgeOps authority path.](../docs/images/ai-diagnose-request.svg)

**[Run the AI + MCP walkthrough →](AI.md)**

## What will open in your browser

Both demos use the real ForgeOps Approval PWA when an Action needs a customer
decision. The exact requester, purpose, operation and target are shown before
anything is released.

![Schematic preview of the customer approval information shown by the browser surface.](../docs/images/customer-approval.svg)

The image above is a checked-in schematic preview, not a browser screenshot. The
demo opens the actual PWA locally. A real capture from the current bundle should
replace this preview when screenshot assets are published.

Demo 2 also opens a local chat page with the connector's live state beside the
conversation so you can compare what the model says with what the target itself
reports.

## Before you start

Both demos use the same first-touch bundle.

```text
Docker           running
curl, python3, lsof, bash
ports free       8010-8012, 8080, 8089, 8093-8095, 18054-18057, 55454
about 1 GB       bundle + Postgres image on first run
```

For Linux-specific setup, see [LINUX.md](LINUX.md).

Want the diagrams before running anything? Start with the
[visual walkthrough](VISUAL-GUIDE.md).

## Which one should I choose?

Start with **Demo 1** if you have not seen ForgeOps before. It establishes the
core claim without involving model behaviour.

Run **Demo 2** next if you want to see the same authority model with a requester
that can inspect symptoms, reason and choose tools dynamically.

The demos are deliberately separate because AI is a requester type, not a second
execution path and not the definition of ForgeOps.
