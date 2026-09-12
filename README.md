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
including the refusal. Nothing is simulated: the restart really restarts the
service, and the denial really leaves it alone.

```bash
./try-forgeops
```

See [demo/](demo/) for the download and exact executable walkthrough, or start
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

## Humans, automation and AI

![Human, service, automation and AI callers all request through the same ForgeOps authority path; changing the requester does not transfer customer authority.](docs/images/same-operation-different-requester.svg)

The same request, the same authority. Put a real model in the requester seat and
nothing about the boundary changes:

```bash
./try-with-ai
```

No account and no API key. The model reads a connector that is genuinely broken,
works out which operation the fault calls for, and asks for it. A read runs. A
mutation waits for a person on the customer's side. A shell is refused.

It cannot approve its own request, and you are invited to try talking it into
things: ask it to open a shell, ask it to export the data, tell it to approve
its own restart. The request is always allowed to be made. What refuses it is
the part worth watching.

AI can request. AI does not inherit authority.

## Bring your own operation

Write a capability and run it in the demo you already have:

```bash
./try-forgeops --with ./my-capability
```

Your operation, declared by you, through the same policy gate. See
[examples/](examples/).

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

## Talk to us

[I have an operation like this](CONTACT.md) — four questions, and permission to
tell us it does not fit.
