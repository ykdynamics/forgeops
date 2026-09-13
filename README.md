# ForgeOps

**Operate your software inside customer environments — without standing access.**

![How ForgeOps works: a requester asks for one named operation; ForgeOps binds it to exact authority; the customer's own policy allows, asks a human, or refuses.](docs/images/request-without-authority.svg)

You request an operation. The customer keeps authority.

```text
read diagnostics        ALLOW   runs immediately
restart the connector   ASK     waits for a person on the customer's side
open a shell            DENY    refused, and nothing happens
```

## In sixty seconds

Your connector, service or appliance runs inside your enterprise customer's
environment. Something goes wrong. You need to look at it, restart it, or apply
a bounded fix.

![The common pattern today: a narrow operational need is solved by granting broad standing access through VPN, SSH, credentials, jump hosts or screen sharing.](docs/images/the-problem-today.svg)

Today that means asking for access: a VPN account, an SSH key, a jump host, a
screen-share with someone who has the credentials. The customer grants standing
access to solve an occasional problem, and then lives with it.

ForgeOps is the other option. You ask for **one named operation**. The customer's
environment decides whether it happens, and runs it with its own credentials.

You never receive SSH, VPN, a customer credential, or a route into the
environment. **The ability to request an operation is not the authority to
perform arbitrary ones.**

## Try it

The demo is a plain download — no account, no email, no form. It runs a fictional
customer connector on your own machine and walks the three outcomes above,
including the refusal.

**The customer system is synthetic. The operation is not.** Diagnostics read its
real state, approval really gates the restart, and a denied operation produces
no target effect.

```bash
./try-forgeops
```

See [demo/](demo/) for the download and exact executable walkthrough. If you are
starting on Linux, use the [Linux tester quick start](demo/LINUX.md). Or start
with the [diagram-first visual walkthrough](demo/VISUAL-GUIDE.md).

## How it works

- [What just happened](docs/concepts/what-just-happened.md) — the path a request
  takes, and who decided what.
- [Why this isn't remote access](docs/concepts/not-remote-access.md) — the
  distinction that matters, and the ways this class of claim gets faked.

## What the demo does and does not prove

[Read this before believing anything above.](docs/concepts/what-this-proves.md)
The local demo runs on one machine, produces no semantic verification, and
carries no artifact identity. Those properties are real and hold elsewhere; the
laptop cannot show them, and the page says which is which.

## Put an AI in the requester seat

![An AI diagnoses a fictional connector, requests one bounded operation through ForgeOps, and customer authority still decides whether anything executes.](docs/images/ai-diagnose-request.svg)

**AI can reason about what to do. It does not decide what it is allowed to do.**

The model receives symptoms from a connector whose fault changes between runs,
works out whether restart, resync, waiting or no action makes sense, and requests
one bounded operation through the same ForgeOps path:

```bash
./try-with-ai
```

A read can run. A mutation can wait for a person on the customer's side. A shell
or data-export request can be refused. The model is deliberately outside the
security boundary: changing the prompt does not change the customer's policy or
let the model approve itself.

**AI can request. AI does not inherit authority.**

See [the AI demo walkthrough](demo/AI.md) for the diagnosis cases, the real
Approval PWA step, adversarial prompts, and exactly what leaves your machine.

## Humans, services and automation use the same path

![Human, service, automation and AI callers all request through the same ForgeOps authority path; changing the requester does not transfer customer authority.](docs/images/same-operation-different-requester.svg)

The caller can change. The trust model does not.

## Bring your own operation

Start from the small worked example, build one bounded operation of your own,
and run it in the demo you already have:

```bash
./try-forgeops --with ./my-capability
```

The demo declares it beside the built-in operations and sends it through the
same Action, placement and customer-side policy path. Start with
[`examples/inventory-check/`](examples/inventory-check/) and the
[adapt-an-operation walkthrough](examples/).

## Have a real operation like this?

Try ForgeOps anonymously first. If the demo or your own capability resembles a
real operation you need inside a customer environment, tell us about that
operation — not just that you liked the demo.

**[Tell us about the operation](https://ykdynamics.com/en/forgeops)**

The short evaluator form asks what runs on the customer side, what operation you
need, how you handle it today, and who should have final authority. It is not a
mailing-list signup and it is not required to download or run ForgeOps.

## Where else this fits

Software vendors operating what they shipped is the sharpest version of the
problem, and it is the one these pages lead with. The underlying primitive —
separating the ability to *request* an operation from the authority to *perform*
one — is more general. See [docs/use-cases/](docs/use-cases/).

## What ForgeOps is not

Not a remote-support tool, an SSH or VPN replacement with a nicer UI, a workflow
engine, an approval app, or an AI agent framework. Each of those puts trust
somewhere else. If the demo reads like one of them to you, that is worth telling
us — see [CONTACT.md](CONTACT.md).

## Status

ForgeOps is early. The demo is real and runs on your machine; the product behind
it is being evaluated with a small number of people rather than sold.

Practically: the binaries are not code-signed, there is no hosted service to sign
up for, and the steps beyond the local demo — running this against an edge you
operate, putting an operation into production — happen with us rather than
self-serve.

## Evaluation terms

This repository is public for **evaluation and testing**, not as an open-source
release. Copyright © 2026 YK Dynamics. All rights reserved. See
[NOTICE.md](NOTICE.md) for the evaluation notice and contact us before reuse,
redistribution, or commercial use beyond evaluation.

## Talk to us

[I have an operation like this](CONTACT.md) — four questions, and permission to
tell us it does not fit.
