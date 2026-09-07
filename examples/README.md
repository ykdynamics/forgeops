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

## Start from the closest thing

The demo's own capabilities are the worked examples — `acme.service.status` for
a read and `acme.service.restart` for a mutation with an effect. Adapting one is
a better first step than writing from scratch, because the declaration is the
part that carries the guarantees.

> **Unresolved.** Which repository an evaluator is pointed at, and how much of it
> they need, is not settled. Today the capability runtime and harness live in an
> internal repository, and sending someone there means sending them into
> engineering material this surface exists to avoid. That needs a real answer
> before this page is useful.

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
