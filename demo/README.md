# Getting the demo bundle

The demo is a local bundle, not a source checkout: you get a tarball, you can
inspect it before running anything, and then it is one command.

## First, ask for it

**Delivery is direct and guided.** There is no download link, and that is
deliberate rather than unfinished.

Email **forgeops@ykdynamics.com**, and tell us the operation you actually have
— see [CONTACT.md](../CONTACT.md) for the four questions worth answering. We
reply with the bundle.

ForgeOps is in private evaluation. An anonymous download would cost us the only
thing this stage is for: knowing who is evaluating it and what problem they
brought. It would also mean shipping to people we cannot help when something
breaks, which at this stage is a real possibility.

Whether this later becomes an authenticated download and then a public one is a
decision that has not been made.

## Then run it

```bash
tar -xzf forgeops-first-touch-*.tar.gz
cd forgeops-first-touch-*
./try-forgeops
```

Prerequisites: Docker, `curl`, `python3`, `lsof`, `bash`, and free local ports.
No account, email, sign-up or source build.

Exercised on macOS on Apple silicon and on Linux x86-64. The bundle carries
binaries for the platform it was built for, so tell us which you are on. Docker
is used for one Postgres container and is pulled on first run; nothing else
needs network access.

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
