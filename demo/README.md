# Getting the demo bundle

The demo is a local bundle, not a source checkout. You get a tarball, you can
inspect it, and you run one command.

```bash
tar -xzf forgeops-first-touch-*.tar.gz
cd forgeops-first-touch-*
./try-forgeops
```

Prerequisites: Docker, `curl`, `python3`, `lsof`, `bash`, and free local ports.
No account, email, sign-up or source build.

Then, if you want to see an AI make the same requests through the same
authority path:

```bash
./try-with-ai-mcp
```

To start over from a clean state:

```bash
bash scripts/first-touch-reset.sh
```

## What is in it

```text
bin/          the ForgeOps runtime and the fictional ACME connector
scripts/      what the entry points run, readable before you run them
docs/         the same concepts as this repository, offline
try-forgeops  the entry point
SHA256SUMS    checksums for everything above
```

Nothing in the bundle phones home, and nothing needs network access except
pulling the Postgres image the first time.

## Getting a copy

> **Unresolved.** ForgeOps is in private evaluation and the bundle is not
> published anywhere yet. Today it is sent directly. How an evaluator obtains
> it — and whether that stays deliberate rather than becoming a download link —
> is part of the publication decision, not something to settle by putting a file
> somewhere convenient.

Ask via [CONTACT.md](../CONTACT.md).
