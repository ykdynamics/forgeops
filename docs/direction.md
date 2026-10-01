# Where this could go

ForgeOps starts with a narrow problem: performing bounded operations inside
customer environments without handing the requester standing access.

The underlying primitive is broader:

**separate the ability to request an operation from the authority required to perform it.**

That pattern can apply wherever execution crosses a trust boundary:

- software vendors operating what they deployed inside customer environments
- central platforms operating workloads in restricted or sovereign environments
- automation requesting changes that remain subject to local policy or human approval
- AI agents selecting and requesting tools without inheriting the authority behind them
- edge and IoT environments where a trusted local gateway performs bounded operations against devices or appliances
- industrial or operational systems where execution remains subject to local policy and safety controls

The target does not have to run ForgeOps itself. A trusted execution point can
sit beside it and use a local API, protocol, credential or capability to perform
the approved operation.

```text
requester
    |
    |  bounded operation
    v
ForgeOps
    |
    |  identity + target + policy + approval
    v
trusted execution point
    |
    |  local authority
    v
software / service / gateway / appliance / device
```

The longer-term direction is not to turn ForgeOps into a fleet platform, an IoT
platform or an AI framework. It is to make the same authority boundary useful
across more kinds of targets and environments — a **governed execution plane for
bounded operations across trust boundaries**.

Different systems can supply the intelligence around that execution. A fleet
platform may detect drift. An AI may diagnose a fault. An operator may request a
restart. ForgeOps remains concerned with the question that follows:

**Should this exact operation, against this exact target, be allowed to happen — and where should the authority to perform it live?**

See [the current use-case collection](use-cases/) for the concrete cases the
project documents today.

---

Back to [the front page](../README.md).
