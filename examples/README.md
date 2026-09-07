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

## What you cannot do yet, stated plainly

You cannot build one of these today without us.

The capability SDK is not independently distributable. It exists, it is small,
and it has no third-party dependencies — but it lives inside a private
repository with no published module, so the ordinary thing a developer would
do fails:

```text
$ go get github.com/ykdynamics/forgeops-capabilities/sdk
404 Not Found — not found: invalid version
```

We could have papered over this by pasting the SDK into this page. We would
rather tell you it is a real gap, because a copied SDK is one you cannot
update and we cannot support.

Until it is fixed, adapting an operation happens with us in the loop: ask via
[CONTACT.md](../CONTACT.md) and we will get you a working starting point. That
is a worse answer than a `go get`, and it is the true one.

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
