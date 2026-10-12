# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 YK Dynamics
"""Protocol tests for forgeops_client, forgeops-request and forgeops-mcp,
against a fake customer ForgeOps on 127.0.0.1.

  python3 -m unittest discover -s clients/python -v

What they hold the clients to:
  - the requester key goes to the token exchange and nowhere else;
  - requests name a capability key (and version), never a guessed revision;
  - the server's answers are shown as given: a disclosed output is passed
    through untouched, a withheld one has nothing to show, and the client never
    filters or reshapes a result itself;
  - the only writes are the token exchange and creating a request: no approval,
    binding, install or transition path exists in these clients.
"""
import json
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import forgeops_client as fc  # noqa: E402

KEY = "fo_requester_key_never_shown"
TENANT = "tenant-eval"

CAPABILITIES = [{
    "capability_key": "demo.service.status", "version": "0.1.1", "environment": "customer-site",
    "target": "demo-service", "capability_revision": 2, "package_digest": "sha256:pkg",
    "description": "Reads the service status.",
    "input_schema": {"type": "object", "required": ["service"]},
    "output": {"disclosure": "approved", "schema": {"type": "object", "properties": {"healthy": {"type": "boolean"}}}},
}]

# What the server sends as payload.result, per disclosure decision.
DISCLOSED = {"status": "succeeded", "disclosure": "disclosed", "output": {"healthy": True, "server_sent_this_too": 7}}
WITHHELD = {"status": "succeeded", "disclosure": "withheld",
            "reason": "the customer has not approved disclosing this capability's result to requesters"}
UNSTATED = {"status": "succeeded", "output": {"healthy": True, "queue_depth": 42}, "error": ""}

WRITES_ALLOWED = {("POST", "/v1/auth/token"), ("POST", "/v1/tenants/%s/actions" % TENANT)}


class FakePlatform:
    def __init__(self):
        self.requests = []          # (method, path, headers, body)
        self.actions, self.transitions = {}, {}
        self.next_result = DISCLOSED
        self.next_status = "succeeded"
        self.refuse_create = None   # (status, body)
        self.create_answer = None   # create the Action, then answer this instead: (status, body) or ("RAW", bytes)
        self.slow_headers = {}      # path -> seconds to spend sending the response headers
        self.odd_reads = False      # transitions arrive in a shape no client expects
        self.redirect = {}          # path -> Location: answer 302 there
        self.slow = {}              # path -> seconds to stall before answering
        self.trickle = {}           # path -> seconds to spend sending the body, a byte at a time
        self.drop_creates = 0       # create the Action, then drop this many answers unanswered
        self.unreadable = False     # every read of an existing Action: connection dropped
        self.empty = False          # nothing is requestable
        self.by_key = {}            # idempotency key -> action id, as the real Platform keeps it
        self.tokens = set()         # session tokens currently valid
        self.lock = threading.Lock()

    def expire_tokens(self):
        """Every token issued so far stops working, as an expiry would."""
        with self.lock:
            self.tokens.clear()

    def handle(self, method, path, headers, body):
        with self.lock:
            self.requests.append((method, path, dict(headers), body))
        if path in self.redirect:
            return "REDIRECT", self.redirect[path]
        if path in self.slow:
            time.sleep(self.slow[path])
        if (method, path) == ("POST", "/v1/auth/token"):
            if (body or {}).get("api_key") != KEY:
                return 401, {"error": "invalid api key"}
            with self.lock:
                token = "session-token-%d" % (len(self.tokens) + sum(1 for r in self.requests if r[1] == "/v1/auth/token"))
                self.tokens.add(token)
            expires = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))
            return 200, {"token": token, "tenant_id": TENANT, "expires_at": expires}
        auth = headers.get("Authorization") or ""
        if not auth.startswith("Bearer ") or auth[len("Bearer "):] not in self.tokens:
            return 401, {"error": "unauthenticated"}
        if (method, path) == ("GET", "/v1/session"):
            return 200, {"subject": "key-1", "tenant_id": TENANT, "workspace_id": "eval", "roles": ["member"]}
        base = "/v1/tenants/%s" % TENANT
        if (method, path) == ("GET", base + "/requestable-capabilities"):
            return 200, {"capabilities": [] if self.empty else CAPABILITIES, "note": "listing is not authority"}
        if method == "GET" and path.startswith(base + "/actions/by-idempotency?key="):
            aid = self.by_key.get(path.split("key=", 1)[1])
            return (200, self.actions[aid]) if aid else (404, {"error": "no action for that idempotency key"})
        if (method, path) == ("POST", base + "/actions"):
            if self.refuse_create:
                return self.refuse_create
            # A repeat of the same intended effect converges on the existing
            # Action (the Platform answers 200 with it).
            existing = self.by_key.get(body.get("idempotency_key"))
            if existing:
                if self.drop_creates:  # the outage goes on: the repeat's answer is lost too
                    self.drop_creates -= 1
                    return "DROP", None
                return 200, self.actions[existing]
            aid = "act-%032x" % (len(self.actions) + 1)
            self.by_key[body.get("idempotency_key")] = aid
            action = {"action_id": aid, "status": self.next_status, "capability_uid": body["capability_uid"],
                      "capability_version": body.get("capability_version") or "0.1.1", "capability_revision": 2,
                      "target": body["target"]}
            self.actions[aid] = action
            msg = {"message_type": "AttemptSucceeded", "payload": {"result": self.next_result}}
            self.transitions[aid] = [
                {"action_id": aid, "from_status": "requested", "to_status": "started", "message": "placed", "by": "control"},
                {"action_id": aid, "from_status": "started", "to_status": self.next_status,
                 "message": json.dumps(msg), "by": "control-callback"}]
            if self.drop_creates:
                self.drop_creates -= 1
                return "DROP", None
            if self.create_answer:
                return self.create_answer
            return 201, action
        if self.unreadable and method == "GET" and "/actions/act-" in path:
            return "DROP", None
        for aid, action in self.actions.items():
            if (method, path) == ("GET", "%s/actions/%s" % (base, aid)):
                return 200, action
            if (method, path) == ("GET", "%s/actions/%s/transitions" % (base, aid)):
                if self.odd_reads:
                    return 200, {"action_id": aid, "transitions": "not a list"}
                return 200, {"action_id": aid, "transitions": self.transitions[aid]}
            if (method, path) == ("GET", "%s/actions/%s/explain" % (base, aid)):
                return 200, {"action": dict(action, failure_reason="the capability reported a failure")}
        return 404, {"error": "not found"}


class Handler(BaseHTTPRequestHandler):
    def _serve(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length)) if length else None
        status, out = self.server.fake.handle(self.command, self.path, self.headers, body)
        if status == "DROP":  # the request was processed; the answer never arrives
            self.close_connection = True
            return
        if status == "RAW":  # an answer that is not JSON
            self.send_response(201)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        spread = self.server.fake.slow_headers.get(self.path)
        if spread:  # headers that keep arriving, each well within any socket timeout
            self.close_connection = True
            try:
                self.wfile.write(b"HTTP/1.1 200 OK\r\n")
                self.wfile.flush()
                deadline = time.monotonic() + spread
                while time.monotonic() < deadline:
                    self.wfile.write(b"X-Slow: 1\r\n")
                    self.wfile.flush()
                    time.sleep(0.1)
                self.wfile.write(b"Content-Length: 2\r\n\r\n{}")
            except OSError:
                pass
            return
        if status == "REDIRECT":
            self.send_response(302)
            self.send_header("Location", out)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        raw = json.dumps(out).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        spread = self.server.fake.trickle.get(self.path)
        if not spread:
            self.wfile.write(raw)
            return
        for i in range(len(raw)):  # a body that arrives, but slowly
            try:
                self.wfile.write(raw[i:i + 1])
                self.wfile.flush()
            except OSError:
                return
            time.sleep(spread / len(raw))

    do_GET = do_POST = do_PUT = do_DELETE = _serve

    def log_message(self, *args):
        pass


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakePlatform()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.fake = self.fake
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.httpd.server_address[1]
        self.tmp = tempfile.TemporaryDirectory()
        self.key_file = os.path.join(self.tmp.name, "requester.key")
        with open(self.key_file, "w") as f:
            f.write(KEY + "\n")

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()
        # The clients' whole write surface: asking for a token, asking for an operation.
        writes = {(m, p) for m, p, _, _ in self.fake.requests if m != "GET"}
        self.assertLessEqual(writes, WRITES_ALLOWED, "a client wrote somewhere a requester has no business writing")

    def session(self):
        return fc.Session(self.url, fc.read_key(self.key_file), net_patience=0)

    def run_tool(self, name, *args):
        env = dict(os.environ, FORGEOPS_URL=self.url, FORGEOPS_KEY_FILE=self.key_file)
        return subprocess.run([sys.executable, os.path.join(HERE, name)] + list(args), env=env,
                              capture_output=True, text=True, timeout=60)

    # -- the key ---------------------------------------------------------

    def test_the_key_goes_to_the_token_exchange_only(self):
        s = self.session()
        s.requestable()
        s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "check")
        token_calls = [r for r in self.fake.requests if r[1] == "/v1/auth/token"]
        self.assertEqual(len(token_calls), 1)
        for method, path, headers, body in self.fake.requests:
            if path == "/v1/auth/token":
                continue
            self.assertNotIn(KEY, path + json.dumps(headers) + json.dumps(body))
            self.assertTrue((headers.get("Authorization") or "").startswith("Bearer session-token-"),
                            "an authenticated call carries the session token, never the key")

    def test_a_key_is_never_sent_over_plain_http_to_another_host(self):
        with self.assertRaises(fc.ForgeOpsError):
            fc.Session("http://forgeops.example.com", KEY, net_patience=0)
        self.assertEqual(self.fake.requests, [])

    def test_a_refused_key_says_so(self):
        with self.assertRaisesRegex(fc.ForgeOpsError, "refused the requester key"):
            fc.Session(self.url, "wrong-key", net_patience=0)

    def other_server(self):
        """A second server, standing for wherever a redirect points."""
        other = FakePlatform()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        httpd.fake = other
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        return other, "http://127.0.0.1:%d" % httpd.server_address[1]

    def test_a_redirect_never_carries_the_token_or_the_key_elsewhere(self):
        other, other_url = self.other_server()
        # After login, a read answers with a redirect to another server.
        s = self.session()
        self.fake.redirect["/v1/tenants/%s/requestable-capabilities" % TENANT] = other_url + "/steal"
        with self.assertRaisesRegex(fc.ForgeOpsError, "redirect"):
            s.requestable()
        # And the token exchange itself, redirected: the key goes nowhere else.
        self.fake.redirect["/v1/auth/token"] = other_url + "/v1/auth/token"
        with self.assertRaisesRegex(fc.ForgeOpsError, "redirect"):
            self.session()
        self.assertEqual(other.requests, [], "a redirect target received a request")

    def test_a_stalled_server_is_a_bounded_wait(self):
        self.fake.slow["/v1/session"] = 3
        started = time.monotonic()
        with self.assertRaisesRegex(fc.ForgeOpsError, "cannot reach"):
            fc.Session(self.url, KEY, net_patience=0, timeout=1)
        self.assertLess(time.monotonic() - started, 2.5)
        # A session time limit bounds a call even when retries would go on.
        s = self.session()
        s.net_patience = 60
        s.time_limit(1.5)
        self.fake.slow["/v1/tenants/%s/requestable-capabilities" % TENANT] = 3
        started = time.monotonic()
        with self.assertRaises(fc.ForgeOpsError):
            s.requestable()
        self.assertLess(time.monotonic() - started, 4)

    def test_a_lost_answer_is_retried_into_the_same_request(self):
        s = fc.Session(self.url, fc.read_key(self.key_file), net_patience=10, sleep=lambda _: None)
        self.fake.drop_creates = 1
        a = s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "check")
        posts = [b for m, p, _, b in self.fake.requests if m == "POST" and p.endswith("/actions")]
        self.assertEqual(len(posts), 2, "the unanswered create is sent again")
        self.assertEqual(posts[0]["idempotency_key"], posts[1]["idempotency_key"], "...as the same intended effect")
        self.assertEqual(len(self.fake.actions), 1, "one effect, not two")
        self.assertEqual(a["action_id"], next(iter(self.fake.actions)))

    # -- requests ----------------------------------------------------------

    def test_listing_is_the_servers(self):
        self.assertEqual(self.session().requestable(), CAPABILITIES)

    def test_a_request_names_key_and_version_never_a_revision(self):
        s = self.session()
        s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "queue stuck", version="0.1.1")
        s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "again")
        posts = [b for m, p, _, b in self.fake.requests if m == "POST" and p.endswith("/actions")]
        self.assertEqual(posts[0]["capability_version"], "0.1.1")
        self.assertNotIn("capability_version", posts[1], "no version given: the server resolves what it serves")
        for b in posts:
            self.assertNotIn("capability_revision", b, "the client must not guess a revision")
            self.assertEqual(b["workspace_id"], "eval", "the workspace is the key's own, from its session")
            self.assertEqual(b["capability_uid"], "demo.service.status")
        self.assertNotEqual(posts[0]["idempotency_key"], posts[1]["idempotency_key"])

    def test_the_servers_refusal_is_reported_as_given(self):
        self.fake.refuse_create = (422, {"error": "not_requestable: demo.service.status is not requestable for target x"})
        with self.assertRaisesRegex(fc.ForgeOpsError, "not_requestable: demo.service.status is not requestable for target x"):
            self.session().request("demo.service.status", "x", {}, "why")

    # -- results, as the server decided them -------------------------------

    def result_for(self, result):
        self.fake.next_result = result
        s = self.session()
        aid = s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "check")["action_id"]
        return s.result(aid), aid

    def test_a_disclosed_output_is_passed_through_untouched(self):
        got, _ = self.result_for(DISCLOSED)
        # Including a field outside the approved schema: what the server sends is
        # the server's decision; the client does not second-guess it either way.
        self.assertEqual(got, DISCLOSED)
        self.assertTrue(fc.disclosure_meaning(got).startswith("disclosed"))

    def test_a_withheld_output_has_nothing_to_show(self):
        got, _ = self.result_for(WITHHELD)
        self.assertEqual(got, WITHHELD)
        self.assertNotIn("output", got)
        self.assertIn("has not approved", fc.disclosure_meaning(got))

    def test_a_result_without_a_decision_is_shown_as_sent(self):
        got, _ = self.result_for(UNSTATED)
        self.assertEqual(got, UNSTATED)
        self.assertIn("stated no disclosure decision", fc.disclosure_meaning(got))

    # -- forgeops-request ----------------------------------------------------

    def test_forgeops_request_shows_the_servers_decisions(self):
        out = self.run_tool("forgeops-request", "list")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("demo.service.status 0.1.1  target demo-service", out.stdout)
        self.assertIn("output  approved", out.stdout)

        self.fake.next_result = DISCLOSED
        out = self.run_tool("forgeops-request", "request", "demo.service.status", "--target", "demo-service",
                            "--purpose", "check", "--input", '{"service":"demo-service"}', "--wait", "0")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('output   {"healthy": true, "server_sent_this_too": 7}', out.stdout)
        self.assertNotIn(KEY, out.stdout + out.stderr)

        self.fake.next_result = WITHHELD
        aid = self.session().request("demo.service.status", "demo-service", {}, "check")["action_id"]
        out = self.run_tool("forgeops-request", "show", aid)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("result   withheld", out.stdout)
        self.assertNotIn("output", out.stdout.replace("the output", ""))

    # -- forgeops-mcp ----------------------------------------------------------

    def mcp(self, *messages):
        env = dict(os.environ, FORGEOPS_URL=self.url, FORGEOPS_KEY_FILE=self.key_file)
        lines = "".join(json.dumps(m) + "\n" for m in messages)
        out = subprocess.run([sys.executable, os.path.join(HERE, "forgeops-mcp")], input=lines, env=env,
                             capture_output=True, text=True, timeout=60)
        self.assertNotIn(KEY, out.stdout + out.stderr)
        return [json.loads(l) for l in out.stdout.splitlines() if l.strip()]

    def test_forgeops_mcp_can_ask_and_never_approve(self):
        self.fake.next_result = DISCLOSED
        replies = self.mcp(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "request_capability", "arguments": {
                "capability_key": "demo.service.status", "target": "demo-service",
                "input": {"service": "demo-service"}, "purpose": "check the queue"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "approve", "arguments": {}}},
        )
        by_id = {r["id"]: r for r in replies}
        self.assertEqual(set(by_id), {1, 2, 3, 4}, "a notification gets no reply")
        self.assertEqual(by_id[1]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual({t["name"] for t in by_id[2]["result"]["tools"]},
                         {"list_capabilities", "request_capability", "get_request"})
        call = json.loads(by_id[3]["result"]["content"][0]["text"])
        self.assertFalse(by_id[3]["result"]["isError"])
        self.assertEqual(call["status"], "succeeded")
        self.assertEqual(call["result"], DISCLOSED, "the result reaches the agent exactly as the server sent it")
        self.assertIn("error", by_id[4], "there is no approve tool")

    def test_forgeops_mcp_stdout_is_only_the_protocol(self):
        """Every stdout line is one JSON-RPC response, whatever goes wrong:
        bad JSON, a batch, an unknown method, a tool error, a refused key."""
        env = dict(os.environ, FORGEOPS_URL=self.url, FORGEOPS_KEY_FILE=self.key_file)
        lines = "\n".join([
            "this is not json",
            json.dumps([{"jsonrpc": "2.0", "id": 1, "method": "ping"}]),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "no/such"}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "request_capability", "arguments": {"capability_key": "demo.service.status"}}}),
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
                "name": "get_request", "arguments": {"request_id": "not-an-id"}}}),
            json.dumps({"jsonrpc": "2.0", "id": 5, "method": "ping"}),
        ]) + "\n"
        out = subprocess.run([sys.executable, os.path.join(HERE, "forgeops-mcp")], input=lines, env=env,
                             capture_output=True, text=True, timeout=60)
        replies = []
        for line in out.stdout.splitlines():
            msg = json.loads(line)  # every line parses
            self.assertEqual(msg.get("jsonrpc"), "2.0")
            self.assertTrue(("result" in msg) != ("error" in msg), "exactly one of result/error: %s" % line)
            replies.append(msg)
        self.assertEqual([r.get("id") for r in replies], [None, None, 2, 3, 4, 5])
        self.assertTrue(replies[3]["result"]["isError"])
        self.assertTrue(replies[4]["result"]["isError"])
        # A refused key is a tool error on stdout's protocol, not a crash.
        with open(self.key_file, "w") as f:
            f.write("wrong-key")
        out = subprocess.run([sys.executable, os.path.join(HERE, "forgeops-mcp")], env=env, capture_output=True, text=True,
                             timeout=60, input=json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                                                           "params": {"name": "list_capabilities", "arguments": {}}}) + "\n")
        reply = json.loads(out.stdout.strip())
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("refused the requester key", reply["result"]["content"][0]["text"])

    # -- one request, one operation ------------------------------------------

    def test_an_unconfirmed_create_hands_back_its_key_and_never_doubles(self):
        s = fc.Session(self.url, fc.read_key(self.key_file), net_patience=0, sleep=lambda _: None)
        self.fake.drop_creates = 1  # created on the server; the answer never arrives
        with self.assertRaises(fc.UnknownOutcome) as caught:
            s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "check")
        key = caught.exception.idempotency_key
        self.assertIn(key, str(caught.exception), "the error names the key to come back with")
        self.assertEqual(len(self.fake.actions), 1)
        # Asking again with that key is the same request, not a second operation.
        again = s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "check", idempotency_key=key)
        self.assertEqual(again["action_id"], next(iter(self.fake.actions)))
        self.assertEqual(len(self.fake.actions), 1)
        self.assertEqual(s.find(key)["action_id"], again["action_id"])
        self.assertIsNone(s.find("request-never-used-0000"))
        out = self.run_tool("forgeops-request", "show", "--idempotency-key", key)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("request  " + again["action_id"], out.stdout)

    def test_forgeops_request_says_plainly_when_nothing_is_requestable(self):
        self.fake.empty = True
        out = self.run_tool("forgeops-request", "list")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "No capabilities are currently requestable with this key.")

    # -- the MCP server, as one long-lived process -------------------------------

    def mcp_process(self, **env):
        p = subprocess.Popen([sys.executable, os.path.join(HERE, "forgeops-mcp")], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             env=dict(os.environ, FORGEOPS_URL=self.url, FORGEOPS_KEY_FILE=self.key_file, **env))
        self.addCleanup(lambda: (p.kill(), p.wait(), p.stdout.close(), p.stderr.close(), p.stdin.close()))

        def send(msg):
            p.stdin.write((msg if isinstance(msg, str) else json.dumps(msg)) + "\n")
            p.stdin.flush()
            reply = json.loads(p.stdout.readline())
            self.assertNotIn(KEY, json.dumps(reply))
            return reply
        return send

    @staticmethod
    def tool(send, mid, name, **arguments):
        reply = send({"jsonrpc": "2.0", "id": mid, "method": "tools/call", "params": {"name": name, "arguments": arguments}})
        return json.loads(reply["result"]["content"][0]["text"]), reply["result"]["isError"]

    def test_forgeops_mcp_hands_back_the_key_of_an_unconfirmed_create(self):
        send = self.mcp_process(FORGEOPS_TOOL_SECONDS="3")
        self.fake.drop_creates = 1000  # created, and no answer ever arrives
        args = dict(capability_key="demo.service.status", target="demo-service",
                    input={"service": "demo-service"}, purpose="check")
        first, is_error = self.tool(send, 1, "request_capability", **args)
        self.assertTrue(is_error)
        self.assertEqual(first["outcome"], "unknown")
        self.assertIn("Do not submit a new request", first["next"])
        self.fake.drop_creates = 0
        second, is_error = self.tool(send, 2, "request_capability", idempotency_key=first["idempotency_key"], **args)
        self.assertFalse(is_error, second)
        self.assertEqual(second["request_id"], next(iter(self.fake.actions)))
        self.assertEqual(len(self.fake.actions), 1, "asking again with the key must not create a second operation")

    def test_forgeops_mcp_returns_the_request_id_when_following_it_fails(self):
        send = self.mcp_process(FORGEOPS_TOOL_SECONDS="4")
        self.fake.unreadable = True  # created; every read of it then fails
        result, is_error = self.tool(send, 1, "request_capability", capability_key="demo.service.status",
                                     target="demo-service", purpose="check")
        self.assertFalse(is_error, "a created request is not an error to retry")
        self.assertEqual(result["request_id"], next(iter(self.fake.actions)))
        self.assertEqual(result["status"], "unknown")
        self.assertIn("do not request it again", result["meaning"])

    def test_forgeops_mcp_renews_an_expired_token_in_the_same_process(self):
        send = self.mcp_process()
        caps, is_error = self.tool(send, 1, "list_capabilities")
        self.assertFalse(is_error, caps)
        self.fake.expire_tokens()  # the session token expires between two calls
        caps, is_error = self.tool(send, 2, "list_capabilities")
        self.assertFalse(is_error, caps)
        self.assertEqual(caps["capabilities"], CAPABILITIES)
        exchanges = [r for r in self.fake.requests if r[1] == "/v1/auth/token"]
        self.assertEqual(len(exchanges), 2, "one sign-in, one renewal")

    def test_forgeops_mcp_bounds_a_whole_call_including_sign_in(self):
        self.fake.slow["/v1/auth/token"] = 6  # signing in alone would take longer than the limit
        send = self.mcp_process(FORGEOPS_TOOL_SECONDS="2")
        started = time.monotonic()
        result, is_error = self.tool(send, 1, "list_capabilities")
        self.assertTrue(is_error, result)
        self.assertLess(time.monotonic() - started, 3.5, "the tool call outran its limit while signing in")
        reply = send({"jsonrpc": "2.0", "id": 2, "method": "ping"})
        self.assertEqual(reply["result"], {})

    def test_a_body_that_trickles_in_cannot_outrun_the_deadline(self):
        s = self.session()
        s.net_patience = 60
        self.fake.trickle["/v1/tenants/%s/requestable-capabilities" % TENANT] = 6
        s.time_limit(1.5)
        started = time.monotonic()
        with self.assertRaises(fc.ForgeOpsError):
            s.requestable()
        self.assertLess(time.monotonic() - started, 2.5)

    def test_every_unconfirmed_create_keeps_its_key(self):
        """Creation is confirmed only by an answer naming the request. A
        gateway error, an answer without an id, or one that is not JSON all
        leave the outcome unknown -- with the key to come back with."""
        s = fc.Session(self.url, fc.read_key(self.key_file), net_patience=0)
        for answer in [(502, {"error": "bad gateway"}), (504, {"error": "gateway timeout"}),
                       (201, {"status": "requested"}), ("RAW", b"<html>proxy</html>")]:
            with self.subTest(answer=answer[0]):
                self.fake.create_answer = answer
                with self.assertRaises(fc.UnknownOutcome) as caught:
                    s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "check")
                key = caught.exception.idempotency_key
                self.fake.create_answer = None
                again = s.request("demo.service.status", "demo-service", {"service": "demo-service"}, "check",
                                  idempotency_key=key)
                self.assertEqual(again["action_id"], self.fake.by_key[key], "the key finds the request the server made")
        self.assertEqual(len(self.fake.actions), 4, "four attempts, four requests: never a duplicate")
        # A refusal is known: not created, and nothing to recover.
        self.fake.refuse_create = (422, {"error": "not_requestable"})
        with self.assertRaises(fc.ForgeOpsError) as caught:
            s.request("demo.service.status", "x", {}, "check")
        self.assertNotIsInstance(caught.exception, fc.UnknownOutcome)

    def test_a_slow_error_body_is_a_handled_failure(self):
        """A timeout while reading an HTTP error's body is a network failure
        like any other -- for a create, an unknown outcome with its key."""
        s = self.session()
        self.fake.refuse_create = (422, {"error": "not_requestable: " + "x" * 200})
        self.fake.trickle["/v1/tenants/%s/actions" % TENANT] = 6
        s.time_limit(1.5)
        started = time.monotonic()
        with self.assertRaises(fc.UnknownOutcome) as caught:
            s.request("demo.service.status", "demo-service", {}, "check")
        self.assertTrue(caught.exception.idempotency_key)
        self.assertLess(time.monotonic() - started, 2.5)
        # A read with no overall deadline (the CLI's): the error's body stalls
        # past the socket timeout -- a ForgeOpsError, not a raw TimeoutError.
        s = fc.Session(self.url, fc.read_key(self.key_file), net_patience=0, timeout=0.5)
        missing = "act-%032x" % 999
        self.fake.trickle["/v1/tenants/%s/actions/%s" % (TENANT, missing)] = 30
        with self.assertRaises(fc.ForgeOpsError):
            s.action(missing)

    def test_headers_that_trickle_in_cannot_outrun_the_deadline(self):
        s = self.session()
        s.net_patience = 60
        self.fake.slow_headers["/v1/tenants/%s/requestable-capabilities" % TENANT] = 6
        s.time_limit(1.5)
        started = time.monotonic()
        with self.assertRaises(fc.OutOfTime):
            s.requestable()
        self.assertLess(time.monotonic() - started, 2.5, "slow headers held the call past its deadline")

    def test_forgeops_mcp_keeps_the_request_id_through_an_unexpected_answer(self):
        send = self.mcp_process()
        self.fake.odd_reads = True  # created; the status then arrives in a shape nobody expects
        result, is_error = self.tool(send, 1, "request_capability", capability_key="demo.service.status",
                                     target="demo-service", purpose="check")
        self.assertFalse(is_error, result)
        self.assertEqual(result["request_id"], next(iter(self.fake.actions)))
        self.assertIn("do not request it again", result["meaning"])

    def test_forgeops_request_recovery_command_is_the_same_request(self):
        self.fake.create_answer = (502, {"error": "bad gateway"})  # sent; never confirmed
        purpose = "queue stuck $(touch /tmp/never) `id`"
        env = {k: v for k, v in os.environ.items() if not k.startswith("FORGEOPS_")}  # options only
        out = subprocess.run([sys.executable, os.path.join(HERE, "forgeops-request"), "--url", self.url,
                              "--key-file", self.key_file, "request", "demo.service.status", "--target", "demo-service",
                              "--purpose", purpose, "--input", '{"service": "demo-service"}', "--version", "0.1.1",
                              "--workspace", "eval", "--wait", "5"],
                             env=env, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(out.returncode, 0)
        command = out.stderr.strip().splitlines()[-1].strip()
        argv = shlex.split(command)  # one shell word per argument, the purpose as plain text
        self.assertEqual(argv[argv.index("--purpose") + 1], purpose)
        self.assertEqual(argv[argv.index("--input") + 1], '{"service": "demo-service"}')
        self.assertEqual(argv[argv.index("--version") + 1], "0.1.1")
        self.assertEqual(argv[argv.index("--workspace") + 1], "eval")
        self.assertEqual(argv[argv.index("--url") + 1], self.url)
        self.assertEqual(argv[argv.index("--key-file") + 1], self.key_file)
        key = argv[argv.index("--idempotency-key") + 1]
        self.assertIn(key, self.fake.by_key, "the printed key is the one the request was sent with")
        # Running it, once the gateway is back, returns the same request.
        self.fake.create_answer = None
        again = subprocess.run([sys.executable, os.path.join(HERE, "forgeops-request")] + argv[1:], env=env,
                               capture_output=True, text=True, timeout=120)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn(self.fake.by_key[key], again.stdout)
        self.assertEqual(len(self.fake.actions), 1)

    def test_forgeops_mcp_survives_malformed_messages(self):
        send = self.mcp_process()
        for mid, msg in enumerate([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": [1]},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": [1]}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": {"a": 1}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_request", "arguments": [1]}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "get_request",
                                                                           "arguments": {"request_id": 7}}},
            {"jsonrpc": "2.0", "id": 6, "method": 5},
            {"jsonrpc": "2.0", "id": {"not": "an id"}, "method": "ping"},
            {"jsonrpc": "2.0", "id": 8, "method": "initialize", "params": {"protocolVersion": ["x"]}},
        ], start=1):
            reply = send(msg)
            self.assertEqual(reply.get("jsonrpc"), "2.0")
            self.assertTrue(("result" in reply) != ("error" in reply), reply)
        # Still alive, still answering.
        self.assertEqual(send({"jsonrpc": "2.0", "id": 99, "method": "ping"})["result"], {})

    def test_forgeops_mcp_reports_a_withheld_result_without_output(self):
        self.fake.next_result = WITHHELD
        replies = self.mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "request_capability", "arguments": {"capability_key": "demo.service.status",
                                                        "target": "demo-service", "purpose": "check"}}})
        call = json.loads(replies[0]["result"]["content"][0]["text"])
        self.assertEqual(call["result"], WITHHELD)
        self.assertTrue(call["result_disclosure"].startswith("withheld"))


if __name__ == "__main__":
    unittest.main()
