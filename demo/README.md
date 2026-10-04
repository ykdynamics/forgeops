# ForgeOps demos

One demo, then the same demo with an AI asking.

Start with **Demo 1**: it shows the whole idea, with you as the customer's
approver. **Demo 2** is the follow-on: the same customer side, with a real model
in the vendor's seat.

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

Recorded on our own hardware (a laptop and a Raspberry Pi whose 3.5" screen
says what the customer's side decided), edited for pace. The download runs the
same thing with every side on your laptop:

![ForgeOps on our hardware with a real AI model: the chat on the vendor's laptop, and the customer's box on its own screen — allowed, approval needed, verified, request blocked.](../docs/images/recording-hardware-ai.webp)

**[Run the AI + MCP walkthrough →](AI.md)**

## What will open in your browser

Both demos use the real ForgeOps Approval PWA when an Action needs a customer
decision. The exact requester, purpose, operation and target are shown before
anything is released.

![Schematic preview of the customer approval information shown by the browser surface.](../docs/images/customer-approval.svg)

The image above is a schematic, not a screenshot. The demo opens the actual PWA
locally, and the recordings on the [front page](../README.md) and in
[Demo 2](AI.md) show the real page.

Demo 2 also opens a local chat page with the connector's live state beside the
conversation so you can compare what the model says with what the target itself
reports.

## Before you start

Both demos use the same first-touch bundle.

```text
Docker           running
curl, python3, lsof, bash
ports free       8010-8012, 8080, 8089, 8093-8095, 18054-18057, 55454
                 plus 8099 if you bring your own operation
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

## Shown on request: the hosted two-site setup

The download puts every side on one laptop, which is also [what it cannot
prove](../docs/concepts/what-this-proves.md): nothing there distinguishes a real
boundary from a program calling itself. So we built the same flow across real
ones: one hosted ForgeOps, two fictional customers on separate networks, a
vendor on its own computer, approvers on their phones. It is not in the
download; we show it live. [Get in touch](../CONTACT.md).

**Two customers, one ForgeOps.** The same vendor asked both customers to restart
their connector at the same moment. Each request appeared only in that
customer's approval inbox, was approved by that customer's own approver, and ran
only on that customer's machine. An approver who tried to decide the other
customer's request was refused.

**An on-premises box.** Customer A's site is a small computer on its own
network, with a screen that says what it decided and did. The vendor's computer
cannot reach it at all: no ping, no port. Every request still arrives, because
the box calls out to ForgeOps; nothing calls in.

**A customer's cloud account.** Customer B's site is a virtual machine in their
own AWS account, created from a template for the session. It has no inbound
port at all: not even for administration, which goes through AWS's own channel.
The network's flow logs, kept as evidence, show zero accepted inbound
connections while it served requests. When the session ends, the machine's
credential is revoked, everything is deleted, and a check proves nothing is
left.

**Approve from your phone.** A held request reaches the approver's lock screen.
Tapping it opens that request, with exactly what the approval will authorize. A
passkey (Face ID) is needed for every approval, and one check approves one
request. [A person decides, on their phone →](../docs/concepts/a-person-decides.md)

**The vendor's AI asks.** An AI agent on the vendor's own computer, given only
the tools to ask and to follow up, requested a restart in its own words,
waited while the customer approved on their phone, and reported the result. It
has no way to approve.

**The team gets the alert.** A customer's Telegram group can be told that a
request is waiting: no details, just a button into the app. The decision is
still made in the app, with a passkey.

**A power cut fails closed.** With a restart waiting for approval, we cut the
power to the customer's box. While it was off, new requests were refused rather
than queued. When it came back, it reconnected by itself and reported the
waiting restart as expired; it never ran.

These were run with synthetic data on our own hardware and accounts. On a hosted
service, the hosting side holds the keys that sign approvals and policy; [what
that means, and where it is going](../docs/concepts/a-person-decides.md#what-this-does-not-prove).
