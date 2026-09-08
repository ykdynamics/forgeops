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

## This step is not self-serve

The demo is a plain download because it costs you nothing and teaches you
something. This step is different: writing an operation means talking about
*your* environment, your target, and who should hold authority over it — and
that is a conversation, not a package.

So building a capability happens with us in the loop. Write to
[forgeops@ykdynamics.com](../CONTACT.md) describing the operation you have in
mind, and we will get you a working starting point for it.

**Two things are true here and we would rather say both.** The gate above is a
choice. Separately, the SDK is not published as a Go module today, so even if
this step were self-serve, the ordinary thing a developer would do would fail:

```text
$ go get github.com/ykdynamics/forgeops-capabilities/sdk
404 Not Found — not found: invalid version
```

It is small and depends on nothing but the standard library, so this is a
publishing decision rather than a hard problem. But we have not made it, and
describing an unbuilt path as a deliberate gate would be the kind of claim this
project tries not to make. We could also have pasted the SDK onto this page;
a copied SDK is one you cannot update and we cannot support.

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
