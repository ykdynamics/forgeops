# Adapt an operation

The demo restarts a fictional connector. The question that matters is whether
your operation fits the same shape.

An operation is a **capability**: a small program that does one thing, declares
what it needs, and returns a result. It runs on the customer side. It is not
given a shell, and it does not choose its own target.

```text
declare    what the operation is, what input it takes, what it may reach
implement  the one thing it does
run        put it through the same ForgeOps authority path as the demo
```

## Start with the worked example

[`inventory-check/`](inventory-check/) is deliberately small:

```text
inventory-check/
  capability.yaml   the operation and its boundary
  main.go           the implementation
```

Read `capability.yaml` first. The manifest is what carries the boundary; the code
only implements it.

The example accepts one target name, `acme-service`, and returns one bounded read.
There is no host, command, path or arbitrary URL in its input. That is intentional:
a capability that accepts arbitrary work is a remote shell with a longer name.

## Build it

The capability SDK is packaged separately rather than published as a Go module
while the external contract is still being evaluated. If you have the SDK kit,
unpack it beside this example and use a local `replace`:

```bash
tar -xzf forgeops-capability-sdk-*.tar.gz
cp -R examples/inventory-check ./my-capability
cd my-capability

cat > go.mod <<'MOD'
module example.com/my-capability

go 1.23

require github.com/ykdynamics/forgeops-capabilities v0.0.0
replace github.com/ykdynamics/forgeops-capabilities => ../forgeops-capability-sdk-<version>
MOD

go build -o inventory-check .
```

If you do not have the SDK kit yet, use [CONTACT.md](../CONTACT.md). The SDK is a
small source bundle, not access to the private ForgeOps repositories.

## Run your operation in the demo you already have

Put the executable beside `capability.yaml` and pass the directory to the first-touch
bundle:

```bash
./try-forgeops --with ./my-capability
```

This is not a mock path. The first-touch harness reads the manifest, declares the
capability, tells the customer-side edge that it hosts it, creates the policy
binding, starts your runtime, and sends the operation through the same canonical
Action, placement and edge-policy path as the built-in demo operations.

The important relationship is:

```text
Capability    what the operation is and the target it may reach
Agent         this customer edge says it hosts the operation
Policy        whether the operation is ALLOW / ASK / DENY
```

A capability can exist and policy can permit it, but placement still refuses it
if the edge has not declared that it hosts the operation. That is intentional:

```text
placement: refused (no_eligible_agent): capability "inventory.check"
is not bound to any eligible agent
```

The customer's side decides what may execute there. Not the requester, and not
policy alone.

## Make it consequential

The worked example is a read, so its manifest says:

```yaml
effect:
  mutation: false
```

For an operation that changes customer state:

```yaml
effect:
  mutation: true
```

The local harness defaults a mutation to **ASK**, so the operation stops for a
customer decision. You can also declare an explicit decision when the exercise
needs it:

```yaml
decision: allow
decision: ask
decision: deny
```

That lets you watch **your operation**, not ours, reach the same authority gate.

## Where the local exercise stops

Running your operation in the laptop demo proves that it fits the capability and
authority model. It does **not** prove production delivery.

A real customer-edge deployment additionally binds an authorized capability
revision to an immutable artifact, customer-local targets and secrets, and the
edge that is allowed to host it. That deeper path is intentionally separate from
the first-touch demo.

If you reached this point with an operation of your own, that is exactly the
signal we care about. Tell us what you built and what customer boundary it needs
to cross:

**[Tell us about the operation](https://ykdynamics.com/en/forgeops)**

## State the delivery guarantee honestly

Every mutating operation has an idempotency owner, and there are only three
honest answers:

```text
the target owns it        re-running is safe because the target makes it safe
the capability owns it    it dedupes, with a declared scope and durability
nobody owns it            the operation is honestly at-least-once
```

The third answer is valid. A read-before-write check does not turn it into
exactly-once execution.
