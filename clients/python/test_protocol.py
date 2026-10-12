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
TOKEN = "session-token-1"
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
        self.redirect = {}          # path -> Location: answer 302 there
        self.slow = {}              # path -> seconds to stall before answering
        self.drop_next_create = False  # create the Action, then drop the connection unanswered
        self.by_key = {}            # idempotency key -> action id, as the real Platform keeps it
        self.lock = threading.Lock()

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
            return 200, {"token": TOKEN, "tenant_id": TENANT, "expires_at": "2026-10-12T12:00:00Z"}
        if headers.get("Authorization") != "Bearer " + TOKEN:
            return 401, {"error": "unauthenticated"}
        if (method, path) == ("GET", "/v1/session"):
            return 200, {"subject": "key-1", "tenant_id": TENANT, "workspace_id": "eval", "roles": ["member"]}
        base = "/v1/tenants/%s" % TENANT
        if (method, path) == ("GET", base + "/requestable-capabilities"):
            return 200, {"capabilities": CAPABILITIES, "note": "listing is not authority"}
        if (method, path) == ("POST", base + "/actions"):
            if self.refuse_create:
                return self.refuse_create
            # A repeat of the same intended effect converges on the existing
            # Action (the Platform answers 200 with it).
            existing = self.by_key.get(body.get("idempotency_key"))
            if existing:
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
            if self.drop_next_create:
                self.drop_next_create = False
                return "DROP", None
            return 201, action
        for aid, action in self.actions.items():
            if (method, path) == ("GET", "%s/actions/%s" % (base, aid)):
                return 200, action
            if (method, path) == ("GET", "%s/actions/%s/transitions" % (base, aid)):
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
        self.wfile.write(raw)

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
            self.assertEqual(headers.get("Authorization"), "Bearer " + TOKEN)

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
        self.fake.drop_next_create = True
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
