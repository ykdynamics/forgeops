# Across real boundaries

Start with the download: [Demo 1 and Demo 2](../demo/README.md) run every side
on your laptop, no account, in minutes. That is the best way to see the idea,
and also [what it cannot prove](concepts/what-this-proves.md): with requester,
authority and target on one machine, nothing distinguishes a real boundary from
a program calling itself.

This page is what comes after. We ran the same flow across real boundaries: one
hosted ForgeOps, two fictional customers on separate networks, a vendor on its
own computer, approvers on their phones. Here is what that showed, and how to
get a place to try it.

## From watching to owning

Each step proves more, and asks more of you.

1. **Watch.** The [hardware recording](../README.md#see-it) on the front page.
   A recording of the real-boundary runs below is coming.
2. **Run it on your laptop.** [Demo 1 and Demo 2](../demo/README.md). No
   account. Start here.
3. **Try the hosted platform.** Invite based, on request: your own sandbox
   customer, an approver account on your phone, a vendor seat (a command-line
   client, or your own AI agent over MCP), and a simulated customer site that we
   run for you. You feel the whole flow without installing anything on your side.
   [Ask for a place](#ask-for-a-place).
4. **Bring your own edge.** The customer side on your own computer or in your own
   cloud account. Evaluation terms come first: who holds which key, and what data
   may cross (synthetic only, until a data processing agreement is signed).
5. **Keys on your side.** The approval and policy keys with you, not with us:
   either ForgeOps run by you, or the hosted one with your phone co-signing every
   approval (a direction, below).

## What we have shown

Run with synthetic data, on our own hardware and accounts, in October 2026.

**Two customers, one ForgeOps.** The same vendor asked both customers to restart
their connector at the same moment. Each request appeared only in that
customer's approval inbox, was approved by that customer's own approver, and ran
only on that customer's machine. An approver who tried to decide the other
customer's request was refused.

**An on-premises box.** Customer A's site is a small computer on its own
network, with a screen that says what it decided and did. The vendor's computer
cannot reach it at all: no ping, no port. Every request still arrives, because
the box calls out to ForgeOps; nothing calls in.

**A customer's cloud account.** Customer B's site is a virtual machine in their
own AWS account, created from a template for the session. It has no inbound
port at all: not even for administration, which goes through AWS's own channel.
The network's flow logs, kept as evidence, show zero accepted inbound
connections while it served requests. When the session ends, the machine's
credential is revoked, everything is deleted, and a check proves nothing is
left.

**Approve from your phone.** A held request reaches the approver's lock screen.
Tapping it opens that request, with exactly what the approval will authorize. A
passkey (Face ID or a fingerprint) is needed for every approval, and one check
approves one request. [A person decides, on their phone →](concepts/a-person-decides.md)

**The vendor's AI asks.** An AI agent on the vendor's own computer, given only
the tools to ask and to follow up, requested a restart in its own words, waited
while the customer approved on their phone, and reported the result. It has no
way to approve.

**The team gets the alert.** A customer's Telegram group can be told that a
request is waiting: no details, just a button into the app. The decision is
still made in the app, with a passkey.

**A power cut fails closed.** With a restart waiting for approval, we cut the
power to the customer's box. While it was off, new requests were refused rather
than queued. When it came back, it reconnected by itself and reported the
waiting restart as expired; it never ran.

## Ask for a place

The hosted platform is invite based, so we can set each place up with you.
[Get in touch](../CONTACT.md) and tell us a little about the operation you would
want to perform inside someone else's environment. You will need a phone that
supports passkeys (any recent iPhone or Android). Data stays synthetic.

## Who holds the keys

On a hosted ForgeOps, we run the control plane, so we hold the key that signs
approvals for the customer's edge and the key that signs its policy. The passkey
proves to ForgeOps who approved; the edge trusts ForgeOps' signature, not the
phone's. Whoever controls the hosted service could therefore approve without a
phone. We say so before anyone connects anything. In the download, those keys
are on your machine.

The direction: **the approver's phone co-signs every approval with the passkey,
and the edge requires both signatures**. A hosted ForgeOps could then not
approve on its own, not even compromised or compelled. The passkey step is in
place; the edge does not check a phone's signature yet.
