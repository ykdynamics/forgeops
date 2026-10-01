# What this demo does and does not prove

Read this before believing anything the demo showed you.

## What it proves

Everything in the local run is real. The connector is a service on your machine
with state you can read. The restart restarts it and the counter moves. The
denial leaves it alone and the counter does not. The shell request is refused by
a policy rule, and the refusal names the rule.

The requester in that run never holds a customer credential, and the approval is
made by a different identity than the one requesting. The first is checked by
the run itself: it fails if the connector's token shows up in the ForgeOps-side
logs (Platform, Control, approval server). The second is set up by `./try-forgeops` (two identities, with
different roles) and *tested* by `./try-with-ai-mcp`: there the requester tries
to approve its own held request with its own credential, and the run fails
unless the server refuses it.

## What it does not prove

**Everything is on one machine.** Requester, authority and target are three
processes on your laptop. Nothing you saw distinguishes that from a program
calling itself. The property only means something across a real boundary, and
the local demo cannot show you one.

**Verification is off unless you turn it on, and even then it is ours.**
ForgeOps can require that a separate, governed capability observe an effect
before it is called verified. In a plain run nothing requires that, so the
restart is evidenced only by the target's own counter and its receipt — a weaker
claim, and we would rather say so than let the word "evidence" carry more than it
should. With `FIRST_TOUCH_VERIFY=1` the restart requires it and a checker on the
edge reports `VERIFIED` beside the execution result. That shows the mechanism.
It does not show independence: the checker is ours, on the same laptop as
everything else.

**No artifact identity.** ForgeOps binds a capability to an immutable artifact by
digest, so that what executes is exactly what was authorized. The binaries in
this bundle were built for the bundle. They carry no digest and prove nothing
about that property.

**One demo is not a product.** It shows one operation shape against one fictional
target, chosen by us.

## Claims are scoped to what produced them

Each level of evaluation proves what it proves. A property demonstrated on the
real estate does not retroactively become true of the laptop demo, and this page
does not get quietly upgraded when a stronger proof exists elsewhere.

![The evaluation ladder: the local demo proves bounded operation, separate approval, refusal and effect; a real private edge adds machine boundary, semantic verification and artifact identity; an evaluator-owned edge adds independence from ForgeOps operators.](../images/evaluation-ladder.svg)

If you ever find a claim on this page that the bundle you were given does not
produce, that is a defect worth telling us about — it is the failure mode this
page exists to prevent.

## Why we are telling you this

An evaluation surface that advertises properties it does not demonstrate is
worse than one that admits the gap — you would have found it, and then
everything else here would be worth less.

The two properties above are real and hold on the actual estate, where the
authorized capability revision carries the verification demand and the artifact
digest decides what may run. Showing that takes an independently operated edge,
not a laptop. If that matters for your case, [tell us](../../CONTACT.md): it is a
better use of your time than a longer local demo.
