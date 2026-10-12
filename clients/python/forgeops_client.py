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

One request is one operation. Every request carries an idempotency key, and the
customer's ForgeOps answers a repeat of the same key with the same request. When
the client cannot tell whether a request was created (the network failed after
it was sent), it says so and hands back that key: asking again with the same key
returns the request if it exists, and never creates a second operation.

Standard library only (Python 3.9+).
"""

import datetime
import http.client
import json
import os
import re
import socket
import threading
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

# A response larger than this is not one a requester client should be reading.
MAX_RESPONSE_BYTES = 1 << 20

# Renew the session token this long before the server says it expires.
TOKEN_MARGIN_SECONDS = 30

IDEMPOTENCY_KEY = re.compile(r"[A-Za-z0-9._:-]{8,128}")


class ForgeOpsError(Exception):
    """A request the client could not make, or the server refused."""


class OutOfTime(ForgeOpsError):
    """The session's time limit ran out."""


class UnknownOutcome(ForgeOpsError):
    """A request was sent, and whether the server created it is not known.

    Asking again with the same idempotency_key returns the request if it was
    created, and creates it once if it was not: never a second operation."""

    def __init__(self, idempotency_key, cause):
        self.idempotency_key = idempotency_key
        super().__init__(
            "the request may or may not have been created (%s). Do not submit a new one: ask again with "
            "idempotency key %s, which returns the same request if it exists" % (cause, idempotency_key))


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect. urllib would replay the Authorization header to
    whatever URL a 3xx names, any host and any scheme; the session token, and on
    the token exchange the key, go only to the URL the requester configured."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # urllib then raises the 3xx as an HTTPError


# The connections an exchange opens, so a deadline can cut one off whatever
# phase it is in -- connecting, sending, reading headers or reading the body.
_exchange = threading.local()


def _tracked(connection_class):
    def make(host, **kw):
        conn = connection_class(host, **kw)
        opened = getattr(_exchange, "connections", None)
        if opened is not None:
            opened.append(conn)
        return conn
    return make


class _TrackedHTTP(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_tracked(http.client.HTTPConnection), req)


class _TrackedHTTPS(urllib.request.HTTPSHandler):
    def https_open(self, req):
        kw = {"context": self._context}
        if hasattr(self, "_check_hostname"):  # Python 3.9 to 3.11
            kw["check_hostname"] = self._check_hostname
        return self.do_open(_tracked(http.client.HTTPSConnection), req, **kw)


_OPENER = urllib.request.build_opener(_NoRedirects, _TrackedHTTP, _TrackedHTTPS)

# Everything that means "the exchange did not complete", whatever the layer.
_NETWORK_ERRORS = (urllib.error.URLError, OSError, http.client.HTTPException)


def _cut(connections):
    """Shut every connection down: a blocked read returns at once. shutdown,
    not just close -- an open response still holds the socket."""
    for conn in connections:
        sock = getattr(conn, "sock", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        try:
            conn.close()
        except Exception:
            pass


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


def new_idempotency_key():
    return "request-" + uuid.uuid4().hex


def check_idempotency_key(key):
    if not isinstance(key, str) or not IDEMPOTENCY_KEY.fullmatch(key):
        raise ForgeOpsError("an idempotency key is 8-128 letters, digits or ._:- (as this client returned it)")
    return key


def error_text(body):
    if isinstance(body, dict) and body.get("error"):
        return str(body["error"])
    return json.dumps(body)[:300] if body else "no detail"


def _expiry(value):
    """The server's RFC 3339 expiry as a POSIX time, or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


class Session:
    """One requester key, one customer's ForgeOps.

    deadline (seconds) bounds everything the session does from construction on,
    authentication included; time_limit() restarts it. Without one, each call
    is bounded only by its own timeouts and net_patience."""

    def __init__(self, url, key, net_patience=60, timeout=30, sleep=time.sleep, deadline=None):
        self.url = check_url(url)
        self.net_patience, self.timeout, self.sleep = net_patience, timeout, sleep
        self.deadline = None if deadline is None else time.monotonic() + deadline
        self._key = key
        self.token, self.token_expires = None, None
        self.tenant, self.workspace = "", ""
        self._authenticate()

    def _authenticate(self):
        """Exchange the key for a session token, and read the session."""
        self.token = None
        status, body = self._send("POST", "/v1/auth/token", {"api_key": self._key})
        if status != 200 or not isinstance(body, dict) or not body.get("token"):
            raise ForgeOpsError("the customer's ForgeOps refused the requester key (%s): %s" % (status, error_text(body)))
        self.token, self.token_expires = body["token"], _expiry(body.get("expires_at"))
        status, me = self._send("GET", "/v1/session")
        if status != 200 or not isinstance(me, dict):
            raise ForgeOpsError("could not read this key's session (%s): %s" % (status, error_text(me)))
        self.tenant = me.get("tenant_id") or body.get("tenant_id") or ""
        self.workspace = me.get("workspace_id") or ""
        if not self.tenant:
            raise ForgeOpsError("the session names no customer tenant")

    def time_limit(self, seconds):
        """Bound everything this session does from now on."""
        self.deadline = time.monotonic() + seconds

    def _remaining(self):
        if self.deadline is None:
            return None
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise OutOfTime("out of time waiting for %s" % self.url)
        return left

    def _pause(self, seconds):
        """Sleep, but never past the deadline."""
        left = self._remaining()
        self.sleep(seconds if left is None else min(seconds, left))

    def call(self, method, path, body=None):
        """(status, decoded JSON) for an authenticated call. The token is
        renewed shortly before it expires, and once if the server rejects it
        (401); the same request -- the same body, so the same idempotency key --
        is then sent again."""
        if self.token_expires is not None and time.time() > self.token_expires - TOKEN_MARGIN_SECONDS:
            self._authenticate()
        status, out = self._send(method, path, body)
        if status == 401:
            self._authenticate()
            status, out = self._send(method, path, body)
        return status, out

    def _send(self, method, path, body=None):
        """One HTTP exchange, retried through network errors for net_patience,
        and never past the deadline: connecting, sending, the response headers
        and the body all count against it."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = json.dumps(body).encode() if body is not None else None
        patience = time.monotonic() + self.net_patience
        while True:
            left = self._remaining()
            timeout = self.timeout if left is None else max(0.05, min(self.timeout, left))
            req = urllib.request.Request(self.url + path, method=method, data=data, headers=headers)
            try:
                status, location, raw = self._exchange(req, timeout)
            except OutOfTime:
                raise
            except _NETWORK_ERRORS as e:
                if time.monotonic() >= patience:
                    raise ForgeOpsError("cannot reach %s (%s)" % (self.url, getattr(e, "reason", e)))
                self._pause(2)
                continue
            if 300 <= status < 400:
                raise ForgeOpsError("%s answered %s with a redirect to %r; redirects are not followed, so "
                                    "neither the key nor the session token leaves %s" %
                                    (self.url, status, location, self.url))
            return status, _decode(raw)

    def _exchange(self, req, timeout):
        """(status, Location header, raw body) for one request. With a
        deadline, the exchange runs beside the caller, and when the deadline
        passes its connections are shut down -- a server sending headers or a
        body slowly, within each socket timeout, cannot hold it any longer."""
        opened, box = [], {}

        def work():
            _exchange.connections = opened
            try:
                try:
                    with _OPENER.open(req, timeout=timeout) as r:
                        box["out"] = (r.status, "", self._read(r))
                except urllib.error.HTTPError as e:
                    # The error's body is read under the same rules as any
                    # body: a failure here is a network failure, not a crash.
                    box["out"] = (e.code, e.headers.get("Location", "") if e.headers else "", self._read(e))
            except BaseException as e:  # handed to the caller as is
                box["err"] = e
            finally:
                _exchange.connections = None

        if self.deadline is None:
            work()
        else:
            worker = threading.Thread(target=work, daemon=True)
            worker.start()
            worker.join(max(0.0, self.deadline - time.monotonic()))
            if worker.is_alive():
                _cut(opened)
                worker.join(1)
                raise OutOfTime("out of time waiting for %s" % self.url)
        if "err" in box:
            raise box["err"]
        return box["out"]

    def _read(self, response):
        """The whole body, a chunk at a time, re-checking the deadline before
        each read: a body trickling in slowly cannot outrun it."""
        chunks, size = [], 0
        while True:
            left = self._remaining()
            _set_read_timeout(response, self.timeout if left is None else max(0.05, min(self.timeout, left)))
            chunk = response.read1(65536) if hasattr(response, "read1") else response.read(65536)
            if not chunk:
                return b"".join(chunks)
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise ForgeOpsError("the response from %s is larger than %d bytes" % (self.url, MAX_RESPONSE_BYTES))
            chunks.append(chunk)

    def _get(self, path, what):
        status, body = self.call("GET", path)
        if status != 200:
            raise ForgeOpsError("%s (%s): %s" % (what, status, error_text(body)))
        if not isinstance(body, dict) or ("error" in body and len(body) == 1):
            raise ForgeOpsError("%s: the server's answer is not the expected JSON object" % what)
        return body

    def requestable(self):
        """What this key may request, as the customer's ForgeOps lists it.
        Listing is not authority: every request is decided when it is made."""
        body = self._get("/v1/tenants/%s/requestable-capabilities" % self.tenant, "could not list capabilities")
        return body.get("capabilities") or []

    def request(self, capability_key, target, input=None, purpose="", version=None, workspace=None,
                idempotency_key=None):
        """Ask for one capability on one target, and return the request.

        The server binds the exact revision (from the version, or what the
        customer's binding serves); the client never guesses one. Pass the
        idempotency_key an earlier attempt returned to ask again without
        risking a second operation. Raises UnknownOutcome when the request was
        sent and its creation could not be confirmed."""
        workspace = workspace or self.workspace
        if not workspace:
            raise ForgeOpsError("this key is not scoped to a workspace: pass the workspace")
        key = check_idempotency_key(idempotency_key) if idempotency_key else new_idempotency_key()
        body = {
            "workspace_id": workspace,
            "capability_uid": capability_key,
            "target": target,
            "input": input if input is not None else {},
            "request_purpose": purpose,
            # A fixed value: the current Action contract requires the field.
            # Nothing here depends on it, and what authority it carries is the
            # server's to decide -- a comment on the client cannot settle that.
            "policy_revision": 1,
            "idempotency_key": key,
            "max_attempts": 1,
        }
        if version:
            body["capability_version"] = version
        try:
            status, action = self.call("POST", "/v1/tenants/%s/actions" % self.tenant, body)
        except ForgeOpsError as e:
            raise UnknownOutcome(key, e)
        except Exception as e:  # anything else the exchange raised: still unknown, never lost
            raise UnknownOutcome(key, "%s: %s" % (type(e).__name__, e))
        if 200 <= status < 300:
            # Accepted -- but only an answer naming the request confirms it.
            if not isinstance(action, dict) or not (action.get("action_id") or action.get("id")):
                raise UnknownOutcome(key, "the server answered %s without a request id" % status)
            action.setdefault("idempotency_key", key)
            return action
        if status >= 500 or status == 408:
            # A gateway or server failure says nothing about whether the
            # operation was accepted upstream.
            raise UnknownOutcome(key, "the server answered %s: %s" % (status, error_text(action)))
        raise ForgeOpsError("the customer's ForgeOps did not accept the request (%s): %s" % (status, error_text(action)))

    def find(self, idempotency_key):
        """The request created under an idempotency key, or None if there is none."""
        key = check_idempotency_key(idempotency_key)
        status, body = self.call("GET", "/v1/tenants/%s/actions/by-idempotency?key=%s" %
                                 (self.tenant, urllib.parse.quote(key, safe="")))
        if status == 404:
            return None
        if status != 200:
            raise ForgeOpsError("could not look up idempotency key %s (%s): %s" % (key, status, error_text(body)))
        return body

    def action(self, action_id):
        return self._get("/v1/tenants/%s/actions/%s" % (self.tenant, action_id), "no request %s" % action_id)

    def explain(self, action_id):
        return self._get("/v1/tenants/%s/actions/%s/explain" % (self.tenant, action_id), "no request %s" % action_id)

    def result(self, action_id):
        """The latest result the server attached to the request, exactly as
        sent, or None while there is none."""
        body = self._get("/v1/tenants/%s/actions/%s/transitions" % (self.tenant, action_id), "no request %s" % action_id)
        return latest_result(body.get("transitions") or [])

    def follow(self, action_id, seconds, on_status=None, stop_when_held=False, reserve=3):
        """Poll until the request ends, is held (if asked), or time runs out.
        With a deadline, `reserve` seconds of it are left for reporting."""
        until = time.monotonic() + max(0, seconds)
        if self.deadline is not None:
            until = min(until, self.deadline - reserve)
        last, a = None, {}
        while True:
            a = self.action(action_id)
            status = a.get("status")
            if status != last and on_status:
                on_status(status)
            last = status
            wait = until - time.monotonic()
            if status in TERMINAL or (stop_when_held and status == "held") or wait <= 0:
                return a
            self._pause(min(2, wait))


def _set_read_timeout(response, seconds):
    """Bound the next socket read. HTTPResponse keeps its socket behind
    fp.raw._sock (CPython 3.9 to 3.13); without it, the connect-time timeout
    applies to each read and the deadline is still checked between chunks."""
    sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
    if sock is not None:
        try:
            sock.settimeout(seconds)
        except OSError:
            pass


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
