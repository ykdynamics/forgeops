# Linux tester quick start

This is the shortest path for a clean Linux machine. The full explanation and trust model remain in [README.md](README.md).

## Requirements

```text
Docker running
curl
python3
lsof
bash
sha256sum
ports free: 8010-8012, 8080, 8089, 8093-8095, 18054-18057, 55454
```

The demo binds its local services to loopback. The basic demo does not open an inbound LAN service.

## x86-64

```bash
BASE=https://eu2.contabostorage.com/d89295baa09047ca80427839e7799618:forgeops/first-touch/8938c080240a
KIT=forgeops-first-touch-linux-amd64.tar.gz

curl -O "$BASE/$KIT"
curl -O "$BASE/$KIT.sha256"
sha256sum -c "$KIT.sha256"

tar --exclude='._*' -xzf "$KIT"
cd "$(tar -tzf "$KIT" 2>/dev/null | cut -d/ -f1 | grep -v '^\._' | head -1)"
./try-forgeops
```

## arm64

```bash
BASE=https://eu2.contabostorage.com/d89295baa09047ca80427839e7799618:forgeops/first-touch/8938c080240a
KIT=forgeops-first-touch-linux-arm64.tar.gz

curl -O "$BASE/$KIT"
curl -O "$BASE/$KIT.sha256"
sha256sum -c "$KIT.sha256"

tar --exclude='._*' -xzf "$KIT"
cd "$(tar -tzf "$KIT" 2>/dev/null | cut -d/ -f1 | grep -v '^\._' | head -1)"
./try-forgeops
```

## Then try the AI requester

After the basic ALLOW / ASK / DENY run works:

```bash
./try-with-ai
```

The model diagnoses a synthetic connector state and requests an operation through the same ForgeOps Action path. If policy returns ASK, the terminal prints a loopback link to the real ForgeOps Approval PWA. Approve or reject there; the target does not execute before that decision.

See [AI.md](AI.md) for the exact model boundary, adversarial prompts to try, and what leaves the machine.

## If something fails

Capture these before cleaning up:

```bash
docker ps -a
ss -lntp 2>/dev/null || true
uname -a
docker version
```

Then include the terminal transcript and which step failed when reporting it.
