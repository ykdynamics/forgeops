# ForgeOps

**Operate your software inside customer environments — without standing access.**

Your connector, service or appliance runs inside your enterprise customer's
environment. Something goes wrong. You need to look at it, restart it, or apply
a bounded fix.

Today that usually means asking the customer for access: a VPN account, an SSH
key, a jump host, a screen-share with someone who has the credentials. The
customer has to grant standing access to solve an occasional problem, and then
live with it.

ForgeOps is the other option. You request a **specific operation**. The customer
environment decides whether it happens.

```text
You ask                 The customer decides           What runs
──────────────────────  ─────────────────────────────  ────────────────────
read diagnostics        allowed automatically          exactly that, nothing else
restart the connector   held until someone approves    exactly that, nothing else
open a shell            refused                        nothing
```

You never receive SSH, VPN, a customer credential, or a route into the
environment. The ability to *request* an operation is not authority to *perform*
arbitrary ones.

## Try it

Fifteen commands is fourteen too many, so there is one:

```bash
./try-forgeops
```

It runs a fictional customer connector on your own machine, then walks through
the three outcomes above against it — including the refusal. Nothing is
simulated: the restart really restarts the service, and the denial really
leaves it alone.

Prerequisites are Docker, `curl`, `python3`, `lsof` and `bash`. No account, no
email, no sign-up, no source checkout.

See [demo/](demo/) for how to get the bundle.

## Then

- [What just happened](docs/concepts/what-just-happened.md) — the path a request
  actually takes, and who decided what.
- [Why this isn't remote access](docs/concepts/not-remote-access.md) — the
  distinction that matters, and the ways it could be got wrong.
- [What this demo does and does not prove](docs/concepts/what-this-proves.md) —
  read this before believing anything above.
- [Adapt an operation](examples/) — make it do something of yours.
- [I have an operation like this](CONTACT.md) — the useful conversation.

## What ForgeOps is not

It is not a remote-support tool, an SSH or VPN replacement with a nicer UI, a
workflow engine, an approval app, or an AI agent framework. Each of those has a
different shape of trust at its centre. If the demo reads like one of them to
you, that is worth telling us — see [CONTACT.md](CONTACT.md).

## Status

ForgeOps is early. The demo below is real and runs on your machine; the product
behind it is being evaluated with a small number of people rather than sold.

What that means practically: the binaries are not code-signed, there is no
hosted service to sign up for, and the parts beyond the local demo — running
this against an edge you operate, building your own operation — happen with us
rather than self-serve. If that is what you want, [say so](CONTACT.md).
