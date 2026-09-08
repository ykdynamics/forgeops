# Run the demo

No account, no email, no form. Download it and run it.

## Download

Pick your platform:

| | |
|---|---|
| macOS, Apple silicon | `forgeops-first-touch-darwin-arm64.tar.gz` |
| macOS, Intel | `forgeops-first-touch-darwin-amd64.tar.gz` |
| Linux, x86-64 | `forgeops-first-touch-linux-amd64.tar.gz` |
| Linux, arm64 | `forgeops-first-touch-linux-arm64.tar.gz` |

```bash
BASE=https://eu2.contabostorage.com/d89295baa09047ca80427839e7799618:forgeops/first-touch/6924153696ef
KIT=forgeops-first-touch-darwin-arm64.tar.gz    # change to match your platform

curl -O "$BASE/$KIT"
curl -O "$BASE/$KIT.sha256"
shasum -a 256 -c "$KIT.sha256"

tar -xzf "$KIT"
cd forgeops-first-touch-*
./try-forgeops
```

Downloading in the terminal is not incidental. The binaries are not code-signed
— we are a small team in private evaluation and have not bought into Apple's
signing programme yet — and macOS attaches a quarantine flag to anything a
browser downloads, which would block them. `curl` does not set that flag, so
nothing is being bypassed or overridden; the demo simply runs.

Check the checksum anyway. It is the only integrity claim we can make right
now, and it is worth more than our assurance.

The path carries a build identifier, so a link always means exactly one build.
Published artifacts are never overwritten — if you come back to this URL later
you get the same bytes, and a newer build lives at a different one.

## What it does

Starts a fictional ACME customer connector on your machine, then walks through
diagnostics that succeed, a restart that waits for approval, and a shell request
that is refused. Nothing is simulated: the restart really restarts the service,
the denial really leaves it alone.

Prerequisites: Docker, `curl`, `python3`, `lsof`, `bash`, and free local ports.
Docker is used for one Postgres container, pulled on first run; nothing else
needs network access, and nothing phones home.

Then, to see an AI make the same requests through the same authority path:

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

**Delivery is direct and guided.** There is no download link, and that is
deliberate rather than unfinished.

```text
you run the demo, or read about it
        |
        v
CONTACT.md — tell us the operation you actually have
        |
        v
we send the bundle directly
        |
        v
local evaluation, with someone available if it misbehaves
```

ForgeOps is in private evaluation. Handing out an anonymous download would cost
us the only thing this stage is for: knowing who is evaluating it and what
problem they brought. It would also mean shipping to people we cannot help when
something breaks, which at this stage is a real possibility.

Whether this later becomes an authenticated download and then a public one is a
decision that has not been made. It is not a gap in this page.

Ask via [CONTACT.md](../CONTACT.md).
