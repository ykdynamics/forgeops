# What ForgeOps borrows from Kubernetes

If you know Kubernetes, most of ForgeOps will look familiar, and that is on
purpose. We took the philosophy: declarative intent, a control plane that
reconciles it, a stable resource API, and the control plane kept apart from
where things actually run. We did not take the machinery. ForgeOps does not run
on Kubernetes and does not need a cluster.

The short version: **Kubernetes schedules workloads onto nodes. ForgeOps
schedules single operations onto customer sites, and the site decides.**

## The same shape

Resources look the way you would expect:

```yaml
apiVersion: forgeops.io/v1
kind: Agent
metadata:
  name: first-touch-edge
spec:
  environment: first-touch
  capabilities:
    - acme.service.status
    - acme.service.restart
    - acme.service.resync
    - acme.service.shell
```

| Kubernetes | ForgeOps | What it is in ForgeOps |
|---|---|---|
| `apiVersion` / `kind` / `metadata` / `spec` / `status` | the same, under `forgeops.io/v1` | desired state in `spec`, what the edge reports in `status` |
| cluster, namespace | **Environment** | one customer site |
| node + kubelet | **Agent** (`forge-agent`) | the edge at the customer's site: it pulls desired state, applies it, reports back |
| `observedGeneration` | `appliedGeneration` | which desired state the edge last applied |
| container image, Pod spec | **Capability** | one named, versioned operation, with its declared effect |
| RBAC, admission control | **Policy** | `allow`, `ask` or `deny` per operation, per edge |
| scheduler | placement | which edge hosts an operation, or why none can (`forgectl resolve`) |
| Deployment rollout | **Rollout** | operation versions advanced environment by environment, with drain, health checks and automatic rollback |
| `kubectl` | `forgectl` | `get`, `get -o wide`, `describe`, `apply -f`, `delete`, `events watch`, `drain` |

## What is deliberately different

**One operation, not a workload.** A Pod keeps running until something stops
it. A ForgeOps Action runs once: it is bound to its exact input, carries an
idempotency key, and its approval can be used a single time. "Restart the
connector" is not something to keep alive. It should happen once, or not at all.

**The edge has the final say.** In Kubernetes, once the API server accepts
something, the kubelet carries it out. In ForgeOps the edge applies the
customer's policy itself, and takes the stricter of that policy and the minimum
the operation declares: an operation that says "a person must approve me" cannot
be quietly switched to `allow`. Anything held for approval runs only with a
signed approval from a separate person, bound to that exact request.

**Fail closed.** Before an edge has synced anything, it denies everything.
Policy reaches it signed, and a forged or replayed policy is rejected.

**No generic exec.** `kubectl exec` gives you a shell in any container you are
allowed into. ForgeOps has no equivalent: a shell would be just another named
operation, and the demo includes one so you can watch the customer's policy
refuse it.

**"It ran" is not "it worked."** A readiness probe tells Kubernetes a container
is up. ForgeOps reports whether the operation ran and whether it had the
intended effect as two separate facts, checked on the customer's side. That is
the `VERIFIED` in the demos.

**Both sides keep the record.** The control plane and the customer's edge each
audit what was asked, decided and done, so neither has to take the other's word
for it.

## Try it

With [Demo 1](../../demo/BASIC.md#if-you-know-kubectl) kept up, these work as
you would expect:

```bash
./bin/forgectl get agents -o wide
./bin/forgectl get capabilities -o wide
./bin/forgectl get policies
```

The demo shows the resources and the decisions. Rollouts and placement across
many sites belong to the product behind it, not to the five-minute download.
