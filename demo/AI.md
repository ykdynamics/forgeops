# Try ForgeOps with AI

**AI can reason about what to do. It does not decide what it is allowed to do.**

The first ForgeOps demo chooses three operations for you. This one puts a real
model in the requester seat and gives it a connector whose symptoms need to be
interpreted first.

![An AI diagnoses a fictional connector, requests one bounded operation through ForgeOps, and customer authority still decides whether anything executes.](../docs/images/ai-diagnose-request.svg)

```bash
./try-with-ai
```

No account and no API key are required for the default demo path.

## What changes — and what does not

The caller changes. The authority model does not.

The model can:

- read the connector state it is given;
- reason about the fault;
- choose whether an operation would help;
- provide arguments and a reason;
- request that operation through ForgeOps.

The model cannot:

- approve its own request;
- turn one capability into another;
- obtain the connector credential;
- open a shell because the prompt asks for one;
- widen the customer policy.

The model is deliberately **outside the security boundary**. A cooperative model
is useful, but the customer-authority boundary is not supposed to depend on the
model cooperating.

## The diagnosis is real enough to be falsifiable

Each run seeds the fictional ACME Sync Connector with one of four states:

| what is wrong | what actually helps |
|---|---|
| workers stopped draining the queue | restart |
| running behind the desired configuration | resync |
| a dependency is timing out | wait |
| nothing is wrong | nothing |

The connector reports symptoms, not the answer. Nothing in its state says
"restart me" or "resync me".

The wrong operation also fails visibly. Restarting a connector whose
configuration is stale brings it back with the same stale configuration. That
keeps this a diagnosis problem rather than a tool-selection performance.

## The path

```text
User: "the connector isn't syncing"
        |
        v
AI reads connector symptoms
        |
        v
AI reasons about what would help
        |
        v
AI requests one named operation
        |
        v
ForgeOps binds requester + operation + target
        |
        v
customer policy
   ALLOW / ASK / DENY
        |
        v
customer-local capability
        |
        v
target effect, or no effect
```

For a consequential operation such as restart, the AI can make the request but
execution stops until the customer-side approval is released.

That distinction is the point:

> **AI chooses what to request. Customer authority decides what may actually happen.**

## Try to break the boundary

Ask the model to open a shell. Ask it to export data. Tell it to approve its own
restart. Tell it that the policy should be ignored.

A well-behaved model may refuse those instructions on its own. That proves
nothing about ForgeOps. Ask it to make the request anyway.

The useful observation is what happens when the requester **does** ask:

```text
AI requests diagnostics      -> ALLOW
AI requests restart          -> ASK -> customer approval
AI requests shell access     -> DENY
AI requests data export      -> DENY
AI says "approve me"         -> still ASK
```

Changing the prompt does not change the customer's authority.

## What leaves your machine

The normal first-touch demo is local. The AI demo is the exception because it
calls a model endpoint.

For the default hosted-model path, the model receives:

```text
sent
  what you type
  the fictional ACME connector state exposed to the requester

not sent by the demo
  arbitrary files from your computer
  the connector credential
  a shell
  a route into the customer environment
```

The model does not receive the customer-side credential used by the capability.
It receives no unrestricted execution channel.

If you prefer to use your own model endpoint, the same requester path can be
pointed at that endpoint instead; see the environment options in
[the full demo runbook](README.md).

## Same operation, different requester

![Human, service, automation and AI callers all use the same ForgeOps authority path.](../docs/images/same-operation-different-requester.svg)

AI is one requester type, not a second execution path and not a special authority
class.

That is why ForgeOps is not an AI-agent framework. The underlying product
property applies equally to software, automation, humans and models:

> **The ability to request an operation is not the authority to perform arbitrary operations.**

## Go deeper

- [Run the basic ALLOW / ASK / DENY demo first](README.md).
- [See what the local demo proves — and what it does not](../docs/concepts/what-this-proves.md).
- [Understand why this is not remote access](../docs/concepts/not-remote-access.md).
- [Bring your own operation](../examples/).
