# Why this isn't remote access with extra steps

The reasonable first reaction is that this is a VPN with a nicer UI. Here is the
actual difference, and the ways it could be got wrong.

![What crosses the customer boundary: operation requests, identity and purpose go in; decisions, results and receipts come back; credentials, secrets, arbitrary commands, inbound routes and standing access do not cross.](../images/trust-boundary.svg)

## The difference

Remote access grants a **capability to act**, then relies on the actor to act
narrowly. Standing SSH into a customer environment lets you do anything the
account can do; that you only ever restart one service is a matter of your
discipline, and the customer's audit log tells them afterwards.

ForgeOps grants **one operation at a time**, decided before it happens. The
requester holds no route and no credential. If the operation was not authorized,
there is nothing to misuse — not a policy against misuse, an absence of the
means.

![Standing access grants broad capability and relies on narrow use; ForgeOps requests a narrow capability and requires explicit authority before execution.](../images/remote-access-vs-forgeops.svg)

## How it could be got wrong

Worth checking, in this or any system claiming the same thing:

**A general-purpose operation.** A capability that accepts an arbitrary command
is a shell with a longer name. The demo includes a shell request specifically so
you can watch it be refused.

**Approval that isn't separate.** If the requester can approve, the hold is
theatre. In `./try-with-ai` the model has no approval tool at all — approval
belongs to a different identity. `./try-with-ai-mcp`, a scripted MCP requester
in the same kit, goes further: it tries to approve its own held restart with its
own credential, and the run fails unless the server refuses (its evidence file
records `refused (HTTP 403), action stayed held, zero target effect`).

**A credential that travels.** If the requester ever holds the customer's token,
the boundary is decorative.

**Authority that lives on the wrong side.** Policy the requester can edit is not
customer authority.

**Evidence produced by the actor.** If the only record of what happened comes
from the thing that did it, it is a claim, not evidence.

That last one is where the local demo is weakest, and we say so in
[what this demo does and does not prove](what-this-proves.md).

## The honest summary

ForgeOps is not a way to get access. It is a way to get **an operation done
without access** — which is worth something only if the operation is narrow, the
authority is genuinely elsewhere, and the refusal is real. Those three are what
to test.
