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
disclosed  the output the customer approved, exactly as the server sent it
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
result   disclosed (the customer approved disclosing this output to requesters)
output   {"healthy": true}
```

A request names the capability and, optionally, its version. The customer's
ForgeOps binds the exact revision it serves; the client never guesses one.

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

## Tests

```bash
python3 -m unittest discover -s clients/python -v
```

The tests run against a fake ForgeOps on 127.0.0.1. They hold the clients to
these rules:
- the key goes to the token exchange only;
- requests carry no guessed revision;
- disclosed, withheld and undecided results are shown exactly as sent;
- the only writes are the token exchange and creating a request.
