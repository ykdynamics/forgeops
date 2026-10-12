# Requester clients

Two small clients for the side that **asks**: a software vendor, or an AI agent
acting for one. Both use a requester key that the customer issued for its own
ForgeOps.

```text
forgeops-request   for a person, on the command line
forgeops-mcp       for an AI agent, as an MCP server (stdio)
forgeops_client.py the request and result handling they share
```

Python 3.9 or later, standard library only. Nothing to install.

## What they can do, and what they cannot

They can **list** what the customer made requestable to the key, **request** one
capability on one target, and **follow** the request to its result.

They cannot approve, bind, install or change anything. That is not a missing
feature: the requester key has no such authority, and the customer's ForgeOps
decides every request when it is made. Whether it runs, where, and after whose
approval is the customer's decision.

The same goes for the result. The customer decides, once, when binding a
capability, whether the output it proposes for requesters may be disclosed. The
clients show the server's answer as given:

```text
disclosed  output the customer's ForgeOps released under the customer's approval,
           exactly as the server sent it
withheld   no output; the server's reason why
none       the capability proposes no output for requesters
```

The clients do no filtering and no authorization of their own. They never hide,
trim or reshape a result. When the output is withheld, there is no output in
the response to show.

## Configure

```bash
export FORGEOPS_URL=https://forgeops.customer.example   # the customer's ForgeOps
export FORGEOPS_KEY_FILE=~/.config/forgeops/requester.key
chmod 600 "$FORGEOPS_KEY_FILE"
```

The key is read from the file, exchanged for a short session token, and never
printed. It is only sent over https, or over plain http to this computer.

## forgeops-request

```bash
./forgeops-request list
./forgeops-request request demo.service.status --target demo-service \
    --input '{"service":"demo-service"}' --purpose "queue stuck since 09:00"
./forgeops-request show act-…
```

```text
demo.service.status 0.1.1  target demo-service  (customer-site, revision 2)
  input   {"properties": {"service": {"type": "string"}}, "required": ["service"], "type": "object"}
  output  approved
          {"properties": {"healthy": {"type": "boolean"}}, "required": ["healthy"], "type": "object"}

request  act-3c1e…
status   succeeded
result   disclosed (the customer's ForgeOps released this output under the customer's approval)
output   {"healthy": true}
```

A request names the capability and, optionally, its version. The customer's
ForgeOps binds the exact revision it serves; the client never guesses one.

If a request was sent but its creation cannot be confirmed, the tool says so
and prints the request's idempotency key, with the command to run next. That
can happen when the network fails, when a gateway answers 5xx, or when the answer
names no request. The command repeats the original request in full: every
option, the same ForgeOps, the same key file, and the key. It is shell-quoted,
so a purpose such as `$(…)` stays text.

```bash
forgeops-request --url https://forgeops.customer.example --key-file ~/.config/forgeops/requester.key \
    request demo.service.status --target demo-service --purpose 'queue stuck since 09:00' \
    --input '{"service":"demo-service"}' --wait 600 --idempotency-key request-4f2a…
forgeops-request show --idempotency-key request-4f2a…
```

The first returns the same request if it was created, and creates it once if it
was not. The second only looks it up. Once a request id has been printed, follow
that request with `show`; do not ask again.

## forgeops-mcp

```bash
claude mcp add forgeops -- /path/to/forgeops-mcp
```

Or, in any MCP client's configuration:

```json
{"mcpServers": {"forgeops": {"command": "/path/to/forgeops-mcp",
  "env": {"FORGEOPS_URL": "https://forgeops.customer.example"}}}}
```

Tools: `list_capabilities`, `request_capability`, `get_request`. There is no
approve tool. A held request waits for the customer's approver, and the agent
follows it with `get_request`.

`request_capability` always returns the `request_id` once a request exists,
even when reading its status then fails, and the tool tells the agent to follow
it rather than ask again. When creation itself could not be confirmed, it
returns `outcome: unknown` with an `idempotency_key`; calling it again with that
key returns the same request.

## Behaviour on the network

- **Redirects are never followed.** A 3xx answer is an error that names where
  it pointed. Neither the session token nor the key leaves the configured URL.
- **Waits are bounded.** Each HTTP call has a timeout, and network errors are
  retried for a while. An MCP tool call answers within 45 seconds in all
  (`FORGEOPS_TOOL_SECONDS`). Signing in, retries and polling count against that
  limit, and so does every part of an answer: its status line, headers and body,
  however slowly each arrives. When the limit is reached, the connection is
  closed.
- **One request is one operation, as long as its key is reused.** Every request
  carries an idempotency key, and the customer's ForgeOps answers a repeat of
  the same key with the same request. Retries inside one call reuse the key on
  their own. When a call cannot confirm that a request was created, it returns
  that key. Asking again with it (`--idempotency-key`, or `idempotency_key` in
  `request_capability`) never creates a second operation; asking again
  *without* it can. Once a request id has been returned, it is the request to
  follow, even if reading its status failed, and even if the answer came in a
  form the client did not expect.
- **Sessions renew themselves.** The session token is renewed shortly before it
  expires, and once if the server rejects it. A long-running MCP server needs
  no restart.
- **`policy_revision` is a fixed value.** The current request contract
  requires the field, so the clients send `1`; nothing on the client side
  depends on it. Whether the field carries any authority is decided by the
  customer's ForgeOps, not by the clients. These clients make no claim about
  it.

## Known limits

- **A held request can expire before anyone approves it.** For example, held
  requests do not survive a restart of the customer's agent. An expired request
  never runs. The tools show its status and the reason the server gives. To try
  again, make a new request without the old idempotency key, which would only
  return the expired request. The customer's approver then decides the new
  request afresh.
- **The output may be withheld because of the customer's agent.** A customer's
  agent that predates execution reporting does not report which implementation
  ran. The customer's ForgeOps then withholds the output and says why, even
  where the binding would otherwise disclose it.

## License

The files in this directory (`clients/python/`) are licensed under the
[Apache License 2.0](LICENSE), so you can embed or adapt them in your own
tools. The rest of this repository is published under its
[evaluation notice](../../NOTICE.md), which this does not change.

## Tests

```bash
python3 -m unittest discover -s clients/python -v
```

The tests run against a fake ForgeOps on 127.0.0.1. They hold the clients to
these rules:
- the key goes to the token exchange only;
- requests carry no guessed revision;
- disclosed, withheld and undecided results are shown exactly as sent;
- the only writes are the token exchange and creating a request;
- an unconfirmed creation always hands back its key, and a known request
  always hands back its id;
- a whole call, slow headers and slow bodies included, stays within its limit.
