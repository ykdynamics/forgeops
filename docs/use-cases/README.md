# Where else this fits

The landing page leads with one problem: a software vendor operating what they
shipped into a customer's environment. That is deliberate. It is the sharpest
version, the easiest to recognise, and the one we are looking for a first design
partner in.

The primitive underneath is more general — **separating the ability to request an
operation from the authority and credentials to perform one** — and these pages
exist so that breadth is discoverable after the first problem lands, rather than
diluting it before.

Read them as *this shape also fits*, not as *we have customers here*. We do not.

## Start with the closest shape

| Situation | What ForgeOps changes | Page |
|---|---|---|
| You ship software into a customer's environment and occasionally need to operate it | replace broad support access with named, customer-governed operations | [Software vendor](software-vendor.md) |
| A pipeline, scheduler or backend must cause a real effect in another authority domain | let the automation request the effect without owning the target credential or approval rule | [Governed automation](governed-automation.md) |
| An AI agent can discover or propose an operational action | let the model ask without inheriting approval authority or customer secrets | [AI agent operations](ai-agent-operations.md) |
| The target sits in a private, regulated or unreachable environment | use an edge-opened outbound session while keeping policy, credentials and execution local | [Sovereign edge](sovereign-edge.md) |

The first three visual walkthroughs deliberately show different requesters and
environments while preserving the same invariant: **the requester is not the
authority simply because it can ask.**
