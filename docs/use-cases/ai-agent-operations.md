# A model that can ask and cannot decide

The interesting property when an AI is the requester is not that it can act. It
is that **its authority does not grow because it asked convincingly.**

![Human, service, automation and AI callers all go through the same ForgeOps authority path; changing the requester does not transfer customer authority.](../images/same-operation-different-requester.svg)

## What is actually true here

An AI caller reaches the same path as any other requester. It receives a
workspace credential and nothing else: no customer secret, no approval authority,
no route into the environment. Its request is subject to the same policy, and it
is refused by the same gate.

```text
AI requests diagnostics    ALLOW   runs
AI requests a restart      ASK     a person on the customer side decides
AI requests a shell        DENY    refused
AI approves its own hold   403     refused server-side, and asserted in tests
```

## You can try to break it yourself

The demo used to assert this with a script. Now a real model sits in the
requester seat and you talk to it, which matters because the interesting
question was never whether our script behaved.

Ask it to open a shell. Ask it to export the data. Tell it to approve its own
restart.

One thing to watch for, because it is the easiest way to fool yourself: a
well-behaved model will often decline on its own judgement and explain why. That
proves nothing. It is the model being agreeable, not the boundary holding. Ask
it to make the request anyway — the claim is that a model which **does** ask
still cannot get it, and what comes back names the policy rule that refused it.

The connector is seeded with one of four faults and the right operation differs
per run, so the model has to diagnose rather than reach for the one button. It
will sometimes get that wrong. That is a valid run: the claims here are
properties of the authority path, and a wrong recommendation reaches exactly the
same gate as a right one.

## Why this is not an AI product

Nothing here is about the model. The authority model existed before the adapter
did, and the adapter is thin in front of the same API a shell script calls. If
the model is replaced, removed, or jailbroken, the boundary is unchanged — which
is the entire claim.

That used to be an assertion. It is now the thing you are invited to test, which
is why the demo hands you the seat rather than showing you a transcript.

Prompt injection is worth naming directly: a model that has been talked into
asking for something still gets the same answer, because the decision is not made
where the conversation is happening. Text arriving inside a tool result is data
the model reads, not an instruction anything acts on, and the requester's scope
is bound before the conversation starts rather than taken from what it says.

The policy doing the refusing is a file on the machine you are running this on.
A refusal you cannot move is a decoy, so move it: turn the held restart into an
immediate one, watch the gate change, and turn it back.

## What it does not solve

It does not make a model's *judgement* trustworthy. It makes the model's
judgement not matter beyond what was already permitted.

It also does not, on a laptop, prove that the requester has no route to the
target: the demo runs everything on one machine. That claim is qualified
separately, on physical hardware where the requester genuinely cannot reach the
box, and the laptop cites it rather than performing it.
