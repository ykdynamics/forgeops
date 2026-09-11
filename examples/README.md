# Adapt an operation

The demo restarts a fictional connector. The question that matters is whether
your operation fits the same shape.

## The shape

An operation is a **capability**: a small program that does one thing, declares
what it needs, and returns a result. It runs on the customer side. It is not
given a shell, and it does not choose its own target.

```text
declare    what the operation is, what input it takes, what it may reach
implement  the one thing it does
authorize  bind it to a revision, and to the artifact that may deliver it
```

## Write one, and run it in the demo you already have

You do not need us for this part any more.

```bash
mkdir my-capability && cd my-capability
# capability.yaml  — what the operation is
# my-capability    — the executable that implements it

./try-forgeops --with ./my-capability
```

The demo declares your operation beside its own, hosts it on the same edge, and
puts it through the same path: a request, a policy decision, and — if you
declared a mutation — a human on the customer side who has to agree.

You will need the SDK to build the executable. It is not published as a Go
module yet, so ask at [forgeops@ykdynamics.com](../CONTACT.md) and we will send
it. That part is still a conversation, and it is a short one.

## Three declarations, and the third is the one that teaches you something

Your `capability.yaml` produces all three:

```text
Capability    what the operation is, and the target it may reach
Agent         that this edge HOSTS it
Policy        allow, ask, or deny
```

The second one is easy to skip and instructive when you do. A capability that
exists, and that policy permits, still cannot run unless the edge says it hosts
it:

```text
placement: refused (no_eligible_agent): capability "inventory.check"
is not bound to any eligible agent
```

The customer's side decides what may execute there. Not the requester, and not
the policy alone.

## The decision comes from what you declare

```yaml
effect:
  mutation: true     # -> ASK. a human decides, every time.
  mutation: false    # -> ALLOW. a read runs on its own.

decision: deny       # or say so outright, and watch it be refused
```

A mutation defaults to asking. You can override it, deliberately, in writing.

## Where this stops

Running your operation in the local demo is not the same as running it in a
customer environment. That needs the implementation pinned and bound to an
authorized revision, on an edge somebody operates — which is a conversation,
and the point at which we would want to know what you built.

## What the contract looks like

Worth knowing even before you can build it, because this is the part that
carries the guarantees rather than the code:

```text
a manifest    names the operation, its input and output, the target it may
              reach, the secrets it requires, and whether its effect needs
              verification
an executable implements exactly that, reads its secret from the edge, and
              never chooses its own target
a revision    binds both to an authorized artifact, so what runs is what was
              approved
```

An operation that accepts an arbitrary command is not a capability, whatever
the manifest says.

## State your guarantee honestly

The one thing worth insisting on. Every operation has an idempotency owner, and
there are only three answers:

```text
the target owns it        re-running is safe because the target makes it safe
the capability owns it    it dedupes, and declares the scope and durability
nobody owns it            it is honestly at-least-once
```

The third answer is fine. Pretending it is the first is not. A read-before-write
check narrows a window; it does not make an operation exactly-once, and a system
that claims otherwise will eventually restart something twice and tell you it
didn't.
