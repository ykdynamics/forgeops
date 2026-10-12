# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 YK Dynamics
"""forgeops_client -- the requester's side of ForgeOps, shared by forgeops-request
and forgeops-mcp.

A requester (a software vendor, or an AI acting for one) holds a requester key
that a customer issued for its own ForgeOps. With it, this module can:

  - list what the customer has made requestable to that key,
  - request one capability, by key (and version), for one target,
  - follow the request and read what the customer's ForgeOps returns.

It decides nothing. Whether an operation may run, where, after whose approval,
and what of its result reaches the requester are the customer's decisions,
enforced by the customer's ForgeOps. This module sends requests and reports the
answers exactly as the server gives them: it does not check authority, and it
never filters, hides or reshapes a result. When the server withholds an output,
there is no output here to show.

Standard library only (Python 3.9+).
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

DEFAULT_KEY_FILE = os.path.expanduser("~/.config/forgeops/requester.key")

# Action states after which nothing more happens to a request.
TERMINAL = frozenset({"succeeded", "failed", "denied", "refused", "expired", "cancelled", "rejected"})

# How the customer's ForgeOps says what of a result it disclosed to this
# requester. The words are the server's; MEANING only explains them.
MEANING = {
    "disclosed": "the customer's ForgeOps released this output under the customer's approval",
    "withheld": "the customer's ForgeOps withheld the output",
    "none": "the capability proposes no output for requesters",
}


class ForgeOpsError(Exception):
    """A request the client could not make, or the server refused."""


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect. urllib would replay the Authorization header to
    whatever URL a 3xx names, any host and any scheme; the session token, and on
    the token exchange the key, go only to the URL the requester configured."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # urllib then raises the 3xx as an HTTPError


_OPENER = urllib.request.build_opener(_NoRedirects)


def read_key(path):
    """The requester key, from a file only: never an argument, never printed."""
    try:
        with open(path) as f:
            key = f.read().strip()
    except OSError as e:
        raise ForgeOpsError("no requester key at %s (%s); the customer issues it" % (path, e.strerror or e))
    if not key:
        raise ForgeOpsError("the requester key file %s is empty" % path)
    return key


def check_url(url):
    """The key goes to this URL: https, or plain http to this computer only."""
    if not url:
        raise ForgeOpsError("no ForgeOps URL: set FORGEOPS_URL or pass --url")
    u = urllib.parse.urlparse(url)
    if u.scheme == "https" and u.hostname:
        return url.rstrip("/")
    if u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost", "::1"):
        return url.rstrip("/")
    raise ForgeOpsError("refusing to send a requester key to %r: use https" % url)


def error_text(body):
    if isinstance(body, dict) and body.get("error"):
        return str(body["error"])
    return json.dumps(body)[:300] if body else "no detail"


class Session:
    """One requester key, one customer's ForgeOps."""

    def __init__(self, url, key, net_patience=60, timeout=30, sleep=time.sleep):
        self.url = check_url(url)
        self.net_patience, self.timeout, self.sleep = net_patience, timeout, sleep
        self.token = None
        self.deadline = None  # monotonic time after which no call starts or waits
        status, body = self.call("POST", "/v1/auth/token", {"api_key": key})
        if status != 200 or not isinstance(body, dict) or not body.get("token"):
            raise ForgeOpsError("the customer's ForgeOps refused the requester key (%s): %s" % (status, error_text(body)))
        self.token = body["token"]
        status, me = self.call("GET", "/v1/session")
        if status != 200:
            raise ForgeOpsError("could not read this key's session (%s): %s" % (status, error_text(me)))
        self.tenant = me.get("tenant_id") or body.get("tenant_id") or ""
        self.workspace = me.get("workspace_id") or ""
        if not self.tenant:
            raise ForgeOpsError("the session names no customer tenant")

    def time_limit(self, seconds):
        """Bound everything this session does from now: no call starts, waits or
        retries past it."""
        self.deadline = time.monotonic() + seconds

    def _remaining(self):
        if self.deadline is None:
            return None
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise ForgeOpsError("out of time waiting for %s" % self.url)
        return left

    def call(self, method, path, body=None):
        """(status, decoded JSON). Network errors and timeouts are retried for a
        while; a retried request is safe, since a request carries its
        idempotency key and the server answers a repeat with the same Action."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = json.dumps(body).encode() if body is not None else None
        patience = time.monotonic() + self.net_patience
        while True:
            left = self._remaining()
            timeout = self.timeout if left is None else max(0.1, min(self.timeout, left))
            req = urllib.request.Request(self.url + path, method=method, data=data, headers=headers)
            try:
                with _OPENER.open(req, timeout=timeout) as r:
                    return r.status, _decode(r.read())
            except urllib.error.HTTPError as e:
                if 300 <= e.code < 400:
                    raise ForgeOpsError("%s answered %s with a redirect to %r; redirects are not followed, so "
                                        "neither the key nor the session token leaves %s" %
                                        (self.url, e.code, e.headers.get("Location", ""), self.url))
                return e.code, _decode(e.read())
            except (urllib.error.URLError, OSError) as e:
                if time.monotonic() >= patience:
                    raise ForgeOpsError("cannot reach %s (%s)" % (self.url, getattr(e, "reason", e)))
                self._remaining()
                self.sleep(2)

    def _get(self, path, what):
        status, body = self.call("GET", path)
        if status != 200:
            raise ForgeOpsError("%s (%s): %s" % (what, status, error_text(body)))
        return body

    def requestable(self):
        """What this key may request, as the customer's ForgeOps lists it.
        Listing is not authority: every request is decided when it is made."""
        body = self._get("/v1/tenants/%s/requestable-capabilities" % self.tenant, "could not list capabilities")
        return body.get("capabilities") or []

    def request(self, capability_key, target, input=None, purpose="", version=None, workspace=None):
        """Ask for one capability on one target. The server binds the exact
        revision (from the version, or what the customer's binding serves); the
        client never guesses one."""
        workspace = workspace or self.workspace
        if not workspace:
            raise ForgeOpsError("this key is not scoped to a workspace: pass the workspace")
        body = {
            "workspace_id": workspace,
            "capability_uid": capability_key,
            "target": target,
            "input": input if input is not None else {},
            "request_purpose": purpose,
            # The Action contract's policy-revision field. It is carried into the
            # decision as stated; the customer's policy decides the request.
            "policy_revision": 1,
            "idempotency_key": "request-" + uuid.uuid4().hex,
            "max_attempts": 1,
        }
        if version:
            body["capability_version"] = version
        status, action = self.call("POST", "/v1/tenants/%s/actions" % self.tenant, body)
        if status not in (200, 201):
            raise ForgeOpsError("the customer's ForgeOps did not accept the request (%s): %s" % (status, error_text(action)))
        return action

    def action(self, action_id):
        return self._get("/v1/tenants/%s/actions/%s" % (self.tenant, action_id), "no request %s" % action_id)

    def explain(self, action_id):
        return self._get("/v1/tenants/%s/actions/%s/explain" % (self.tenant, action_id), "no request %s" % action_id)

    def result(self, action_id):
        """The latest result the server attached to the request, exactly as
        sent, or None while there is none."""
        body = self._get("/v1/tenants/%s/actions/%s/transitions" % (self.tenant, action_id), "no request %s" % action_id)
        return latest_result(body.get("transitions") or [])

    def follow(self, action_id, seconds, on_status=None, stop_when_held=False):
        """Poll until the request ends, is held (if asked), or time runs out."""
        deadline, last, a = time.monotonic() + max(0, seconds), None, {}
        if self.deadline is not None:
            deadline = min(deadline, self.deadline - 3)  # leave time to report
        while True:
            a = self.action(action_id)
            status = a.get("status")
            if status != last and on_status:
                on_status(status)
            last = status
            if status in TERMINAL or (stop_when_held and status == "held") or time.monotonic() >= deadline:
                return a
            self.sleep(2)


def _decode(raw):
    try:
        return json.loads(raw or b"{}")
    except ValueError:
        return {"error": raw[:300].decode("utf-8", "replace") if raw else "empty response"}


def latest_result(transitions):
    """payload.result of the last transition that carries one, untouched."""
    found = None
    for t in transitions:
        try:
            message = json.loads(t.get("message") or "")
        except (TypeError, ValueError):
            continue
        payload = message.get("payload") if isinstance(message, dict) else None
        if isinstance(payload, dict) and "result" in payload:
            found = payload["result"]
    return found


def disclosure_meaning(result):
    """One line saying what the server decided about the output, in its words."""
    if not isinstance(result, dict):
        return "no result recorded"
    decision = result.get("disclosure")
    if decision is None:
        return "the server stated no disclosure decision; the result is shown as it was sent"
    meaning = MEANING.get(decision, "a disclosure decision this client does not know; shown as it was sent")
    if result.get("reason"):
        meaning += ": " + str(result["reason"])
    return "%s (%s)" % (decision, meaning)
