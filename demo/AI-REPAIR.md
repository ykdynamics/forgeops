# Demo 3 — AI repair without the secret

This local evaluation candidate lets a visitor's AI diagnose and repair a
fictional application while its customer-local dummy credential stays on the
customer side.

The supported configuration is deliberately narrow: an **Apple silicon Mac**,
Docker Desktop with Compose v2, and VS Code with Dev Containers. Everything
except the configured AI model runs locally. No ForgeOps account, private
source checkout, developer registry credential or database edit is required.

## Download the qualified candidate

The published file is the exact archive that passed builder qualification; its
filename and bytes have not been changed.

```bash
TAG=ai-demo-eval.1
KIT=forgeops-ai-demo-ai-demo-5-candidate-2-darwin-arm64.tar.gz
curl -LO "https://github.com/ykdynamics/forgeops/releases/download/$TAG/$KIT"
echo "b4d2b96d802bdc4543a144228bdf1e3c565d2b4f08cf4740551eaa1ddf7b8972  $KIT" | shasum -a 256 -c -
tar --exclude='._*' -xzf "$KIT"
cd forgeops-ai-demo-ai-demo-5-candidate-2-darwin-arm64
```

The archive is covered by the repository's [evaluation notice](../NOTICE.md).
It contains packaged executables and synthetic data for evaluation; ForgeOps is
not published as open source by this download.

## Prerequisites

- Apple silicon Mac; the candidate is `darwin/arm64`.
- Docker Desktop with Compose v2 and at least 2 GiB memory available.
- VS Code with the Dev Containers extension.
- `bash`, `curl`, `python3`, `openssl`, `lsof` and `shasum` on the host.
- About 1 GiB free disk.
- Free host ports 8010–8012, 8080, 8420–8424, 18055, 18057 and 55464.
- Normal access for the supported AI client. Authenticate it from inside the
  supplied Dev Container; do not mount host credentials or add host sockets.

The builder-qualified environment used macOS 26.3.1, Docker client 29.3.0 /
server 29.7.2, Compose 5.5.0, VS Code 1.139.1 and Dev Containers 0.469.0. The
requester image and Codex CLI 0.155.0 are pinned in `manifest.env`.

Run the preflight before starting:

```bash
./preflight
```

## Start the customer side and requester

The internal configuration is synthetic, but returning it to the AI is still a
disclosure decision. The environment flag records your consent to that output:

```bash
AI_DEMO_DISCLOSE_INTERNAL_CONFIG=1 ./start
./health
./open-customer-view
./open-approval
./open-requester
```

VS Code opens the supplied workspace. Reopen it in the Dev Container, confirm
`codex --version` reports the version in `manifest.env`, and authenticate the
AI client there if needed. The customer status and approval pages remain in the
host browser, outside the requester container.

Ask:

> Find out why this application is disconnected and fix it.

Use the included `WALKTHROUGH.md` as the presenter guide. It takes you through
this sequence:

1. Read the setup guide and connector status: **ALLOW**, with no approval.
2. Request `internal-config`: **ASK**. Reject it first; submit a fresh request
   and approve the exact synthetic document.
3. Request `secrets-env`: **DENY**. No approval card appears and a person cannot
   override the policy refusal.
4. Request the fixed repair: **ASK**. Reject it and confirm the customer page
   remains **Disconnected** with repair count 0.
5. Submit a fresh repair and approve it. The customer page changes to
   **Connected**, credential state **current**, repair count 1.
6. Read status again. The assistant may claim success only after this separate
   observation; it receives the safe result, never the dummy credential.

When finished:

```bash
./reset
```

Reset removes this demo's state and containers. The next run creates new
identities and a new dummy credential; an earlier approval cannot authorize it.

## Check the requester boundary

Startup runs the boundary check automatically. You can repeat it:

```bash
docker compose -f requester/compose.yaml -p forgeops-ai-demo \
  exec -T requester bash /verify-requester.sh
```

The requester has no protected customer documents, dummy credential, approval
credential, Docker socket, host-home mount, customer runtime/admin route or
direct connector route. Container isolation limits what the AI process can
reach; ForgeOps policy separately decides which declared operation is allowed,
held for a customer, or refused.

## What this candidate has proved

On 2026-10-14, the exact archive above passed 20 of 20 automated cases across
two clean installations. The matrix covered ALLOW/ASK/DENY, reject then fresh
approve, replay without a second effect, changed-input refusal, requester
revocation, agent restart, held-Action expiry, implementation substitution,
secret-canary absence, reset and rerun. All packaged implementation bytes and
the checksummed review evidence matched. The first allowed result completed in
19.5 seconds and the independently observed repair in 41.5 seconds after the
scenario began.

This is **builder qualification**. A person unfamiliar with the implementation
has not yet completed the included `OUTSIDER-REVIEW.md`, so the candidate is not
claimed as independently validated. Running it and returning that completed,
sanitized record would provide the missing evaluation.

It demonstrates one fictional application on one Apple silicon configuration.
It does not establish production readiness, safety for arbitrary AI clients,
offline model operation, support for other host platforms, or customer demand.
The checker, target and ForgeOps components still run on one evaluator-owned
Mac; this local run does not demonstrate a real customer/vendor machine
boundary.

## Share evidence without sharing secrets

For selected synthetic Action IDs, the kit can export a minimized receipt:

```bash
./evidence act-... act-... > ai-demo-evidence.json
```

The export retains Action identity, capability revision, target, input hash,
terminal status and declared safe output. It removes document contents and
unknown output fields. Review the file before sharing it.

Questions, confusing steps and completed unfamiliar-evaluator records are
welcome through [the contact routes](../CONTACT.md).
