# Automation that needs a real effect

A pipeline, scheduler or backend service that must do something consequential in
an environment it does not own.

The usual answer is a service account with standing permissions, which is the
same trade as a human's VPN with none of the hesitation — nobody pauses before
granting a robot broad access, because there is no person to feel uneasy about
it.

## The shape

```text
the automation asks for one operation
the environment's policy decides, without the automation being present
the effect happens with the environment's own credential
the record says what ran, where, and on whose authority
```

## What it is good for

Operations where the decision is stable but the *timing* is not: a nightly job
that occasionally needs to restart something, a deployment that sometimes has to
touch a system in another domain, a remediation that should be automatic during
business hours and gated outside them.

The policy carries that distinction. The automation does not have to.

## What it does not solve

If the automation needs to make a novel decision in the moment, this is the wrong
tool. A bounded operation is one you can name in advance.
