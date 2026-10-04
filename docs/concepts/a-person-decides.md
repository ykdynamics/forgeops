# A person decides, on their phone

A held operation waits for a person on the customer's side. This page is about
that moment: how the person is reached, what they see, and what it takes for
their "yes" to count. Everything here was shown on our hosted two-site setup in
October 2026 (see [across real boundaries](../real-boundaries.md));
it is not in the download.

## What the approver does

Their phone shows *Approval needed: a request is waiting for your decision*.
Tapping it opens the request in the Approval app (installed from the browser,
no app store). The page shows exactly what the approval will authorize: the
operation, the target, the input, and a hash that pins that input. They tap
**Approve**, confirm with Face ID or a fingerprint, and the customer's edge runs
the operation and checks it worked.

## A passkey for every approval, used once

Being signed in is not enough to approve. Each approval asks for the person's
**passkey** again (Face ID, a fingerprint, the phone's screen lock), and the
server accepts an approval only with a passkey check made moments before it.

A check also approves **one thing only**. Approving a second request asks again,
even seconds later. We found the gap ourselves: in a test, a second approval 84
seconds after the first went through on the same check. Since then, two
approvals 47 seconds apart each needed their own Face ID, and a check already
used is refused even when two approvals are sent at the same instant.

What this rules out: a left-open browser, a stolen session, or a script holding
a person's sign-in cannot approve on its own. Approval needs the person, with
their device, at that moment, for that request.

Each decision is recorded with how it was made: who, when, and that a passkey
was confirmed for it.

## An AI can ask, never approve

The requester can be a person at a terminal or an AI agent. We ran an
open-source agent on the vendor's own computer, given **only** three tools:
list what may be asked, ask, and follow what was asked. It had no shell, no
files, no browser. Told that a customer's connector was stuck, it asked for a
restart in its own words; the customer approved on their phone with a passkey;
the agent then reported that the restart had run.

There is no tool to approve, and adding one would not help: approval needs the
customer's passkey, which no agent has.

## Alerts tell; the app decides

A waiting request can reach the customer's team as a phone notification and as
a message in their own Telegram group. Both say only that a request is waiting,
with a button into the app: no customer name, no operation, no target, since a
group can include people who are not approvers. Nothing is decided in a chat.

One practical limit: on iPhone, a chat app's built-in browser cannot use
passkeys. Set the chat app to open links in Safari or Chrome, or treat the
message as the alert and approve in the app.

## What this does not prove

**On a hosted service, the server signs.** In the hosted setup, ForgeOps runs on
our server, so we hold the key that signs approvals for the edge, and the key
that signs its policy. The passkey proves to ForgeOps who approved; the edge
trusts ForgeOps' signature, not the phone's. Whoever controls that server could
therefore approve without a phone. For our own demonstration that is acceptable,
and a partner is told so in writing before connecting anything. In the
download, those keys are on your machine.

The direction, not a claim: **the approver's phone co-signs each approval with
the passkey, and the edge requires both signatures**. A hosted ForgeOps could
then not approve on its own, not even compromised or compelled. Today's passkey
step is the groundwork; the edge does not check a phone's signature yet. See
[who holds the keys](../real-boundaries.md#who-holds-the-keys).
