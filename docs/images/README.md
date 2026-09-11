# Images

Diagrams for the public surface. Two rules.

**They are checked in as SVG, not exported raster.** An SVG is text: it diffs,
it can be corrected in a pull request, and it stays sharp. A PNG dropped in from
a design tool is a binary nobody can edit, and it goes stale silently while the
product moves.

**Every claim in a diagram must be true of the thing being downloaded.** These
are read by people deciding whether to trust the software. A diagram is a claim
like any other sentence on these pages, and the same rule applies: if the demo
does not do it, it does not go in the picture.

## What is here

```text
request-without-authority.svg   the defining one: requester, ForgeOps, the
                                trust boundary, customer policy, capability,
                                target
```

## Still wanted

```text
the-problem.svg        standing access today, before ForgeOps appears at all
what-crosses.svg       what passes the boundary and what does not
who-decides.svg        ALLOW / ASK / DENY as three visible outcomes
same-operation.svg     human, automation and AI through one authority model
```

The first three have a drafted design. `same-operation.svg` should come last:
it only makes sense once ForgeOps itself has been explained, and leading with it
would read as an AI product.
