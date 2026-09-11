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
request-without-authority.svg   landing-page mental model: requester, ForgeOps,
                                trust boundary, customer policy, capability,
                                target

trust-boundary.svg              what crosses into/out of the customer environment,
                                and what deliberately stays customer-local

demo-allow-ask-deny.svg         first-touch demo outcomes: diagnostics ALLOW,
                                restart ASK, shell DENY

demo-three-sides.svg            demo topology: vendor, ForgeOps and customer-side
                                processes, including the edge-opened session
```

The diagrams deliberately overlap only at the concepts that need reinforcing.
The landing image answers "what is ForgeOps?"; the boundary image answers "why
is this not remote access?"; the demo images answer "what will I actually see?"
and "what is running where?".

## Still wanted

```text
the-problem.svg        standing access today, before ForgeOps appears at all
same-operation.svg     human, automation and AI through one authority model
```

`same-operation.svg` should come after ForgeOps itself has been explained. AI is
a useful caller of the platform, not the product definition.
