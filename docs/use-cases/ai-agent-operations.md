# A model that can ask and cannot decide

The interesting property when an AI is the requester is not that it can act. It
is that **its authority does not grow because it asked convincingly.**

![Human, service, automation and AI callers all go through the same ForgeOps authority path; changing the requester does not transfer customer authority.](../images/same-operation-different-requester.svg)

## What is actually true here

An AI caller reaches the same path as any other requester. It receives a
workspace credential and nothing else: no customer secret, no approval authority,
no route into the environment. Its request is subject to the same policy, and it
is refused by the same gate.

The demo checks the part that matters by having the model **attempt to approve
its own held request**. It is refused, and the run fails if it ever is not.

```text
AI requests diagnostics    ALLOW   runs
AI requests a restart      ASK     a person on the customer side decides
AI requests a shell        DENY    refused
AI approves its own hold   403     the run fails if this ever succeeds
```

## Why this is not an AI product

Nothing here is about the model. The authority model existed before the adapter
did, and the adapter is thirty lines in front of the same API a shell script
calls. If the model is replaced, removed, or jailbroken, the boundary is
unchanged — which is the entire claim.

Prompt injection is worth naming directly: a model that has been talked into
asking for something still gets the same answer, because the decision is not made
where the conversation is happening.

## What it does not solve

It does not make a model's *judgement* trustworthy. It makes the model's
judgement not matter beyond what was already permitted.
