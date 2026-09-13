#!/usr/bin/env python3
"""Tiny browser surface for #554 first-touch approval.

This is not an approval model. It is a local browser wrapper around Platform's
proposal APIs: list/review/decide still happen through the canonical Platform
ledger, and Platform signs the approval grant that Control transports to the
edge.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import threading
import urllib.error
import urllib.request


PLATFORM = os.environ["FIRST_TOUCH_PLATFORM"].rstrip("/")
TENANT = os.environ["FIRST_TOUCH_TENANT"]
WORKSPACE = os.environ.get("FIRST_TOUCH_WORKSPACE", "ws-1")
JWT = os.environ["FIRST_TOUCH_APPROVER_JWT"]

# Phone approval (#568). Off by default: the baseline journey binds loopback and
# is unchanged for anyone who never picks up a phone.
#
# Turning it on makes this surface reachable from the local network, which is
# the whole point and also the risk. The listing page stays loopback-only --
# anything on the network that could open "/" could approve everything held --
# so the only path reachable off-box is a per-proposal link carrying an
# unguessable token. The token names ONE proposal and is consumed by the first
# decision, so a forwarded or shoulder-surfed link cannot approve something else
# later, and cannot be replayed.
PHONE = os.environ.get("FIRST_TOUCH_PHONE", "") == "1"

_tokens = {}          # token -> proposal id
_spent = set()        # tokens already used for a decision
_lock = threading.Lock()


def token_for(pid):
    """One stable token per proposal, minted on demand."""
    with _lock:
        for tok, p in _tokens.items():
            if p == pid:
                return tok
        tok = secrets.token_urlsafe(16)
        _tokens[tok] = pid
        return tok


def proposal_for_token(tok):
    with _lock:
        if tok in _spent:
            return None
        return _tokens.get(tok)


def spend(tok):
    with _lock:
        _spent.add(tok)


def platform(method, path, body=None):
    data = None
    headers = {"Authorization": "Bearer " + JWT}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(PLATFORM + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


def html_escape(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class Handler(BaseHTTPRequestHandler):
    def loopback(self):
        return self.client_address[0] in ("127.0.0.1", "::1")

    def card(self, pid, capability, target, purpose, action_prefix):
        return f"""
                  <section>
                    <h2>ACME Support wants to restart ACME Sync Connector</h2>
                    <dl>
                      <dt>Reason</dt><dd>{purpose or "Connector has 17 pending jobs."}</dd>
                      <dt>Requested operation</dt><dd>{capability}</dd>
                      <dt>Target</dt><dd>{target}</dd>
                    </dl>
                    <form method="post" action="{action_prefix}/deny"><button class="secondary">Deny</button></form>
                    <form method="post" action="{action_prefix}/approve"><button>Approve</button></form>
                  </section>
                """

    def do_GET(self):
        # A per-proposal link is the only thing reachable from the network.
        if self.path.startswith("/p/"):
            tok = self.path[3:].strip("/")
            pid = proposal_for_token(tok)
            if not pid:
                # Same answer for "never existed" and "already decided": a link
                # that has been used should not confirm it once was valid.
                self.send_error(404, "this approval link is not valid")
                return
            try:
                review = platform("GET", f"/v1/tenants/{TENANT}/proposals/{pid}/review")
                what = review.get("what", {})
                body = self.card(pid,
                                 html_escape(what.get("capability_uid", "")),
                                 html_escape(what.get("target", "")),
                                 html_escape(review.get("why", {}).get("caller_purpose", "")),
                                 f"/p/{html_escape(tok)}")
                self.send_page(self.wrap(body))
            except Exception as exc:
                self.send_error(502, str(exc))
            return

        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        # The listing shows everything held. Anything that could open it could
        # approve all of it, so it never leaves this machine.
        if PHONE and not self.loopback():
            self.send_error(403, "open the per-approval link instead")
            return
        try:
            props = platform("GET", f"/v1/tenants/{TENANT}/proposals?workspace_id={WORKSPACE}").get("proposals", [])
            open_props = [p for p in props if p.get("status") == "open"]
            cards = []
            for p in open_props:
                review = platform("GET", f"/v1/tenants/{TENANT}/proposals/{p['proposal_id']}/review")
                capability = html_escape(review.get("what", {}).get("capability_uid", p.get("capability_uid", "")))
                target = html_escape(review.get("what", {}).get("target", p.get("target", "")))
                purpose = html_escape(review.get("why", {}).get("caller_purpose", ""))
                pid = html_escape(p["proposal_id"])
                card = self.card(pid, capability, target, purpose, f"/{pid}")
                if PHONE:
                    tok = token_for(p["proposal_id"])
                    link = f"http://{LAN_HOST}:{PORT}/p/{tok}"
                    card += f'<p class="phone">On a phone on this network: <code>{html_escape(link)}</code></p>'
                cards.append(card)
            if not cards:
                cards.append("<section><h2>No open approvals</h2><p>Waiting for a held ForgeOps operation.</p></section>")
            page = self.wrap("".join(cards))
            self.send_page(page)
        except Exception as exc:
            self.send_error(502, str(exc))

    def wrap(self, body):
        return f"""<!doctype html>
              <meta charset="utf-8">
              <title>ForgeOps first-touch approval</title>
              <style>
                body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 760px; color: #172033; }}
                section {{ border: 1px solid #ccd3dd; border-radius: 8px; padding: 1.25rem; margin: 1rem 0; }}
                h1, h2 {{ margin-top: 0; }}
                dl {{ display: grid; grid-template-columns: 12rem 1fr; gap: .5rem 1rem; }}
                dt {{ font-weight: 700; color: #445066; }}
                form {{ display: inline-block; margin-right: .75rem; }}
                button {{ font: inherit; padding: .65rem 1rem; border-radius: 6px; border: 1px solid #15233a; background: #15233a; color: white; cursor: pointer; }}
                .secondary {{ background: white; color: #15233a; }}
              </style>
              <h1>Customer Approval</h1>
              <p>The requester can ask for this operation. The customer decides whether it runs.</p>
              {body}
            """

    def send_page(self, page):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def do_POST(self):
        parts = self.path.strip("/").split("/")
        tok = None
        if len(parts) == 3 and parts[0] == "p" and parts[2] in ("approve", "deny"):
            tok, verb = parts[1], parts[2]
            pid = proposal_for_token(tok)
            if not pid:
                self.send_error(404, "this approval link is not valid")
                return
        elif len(parts) == 2 and parts[1] in ("approve", "deny"):
            # The loopback listing decides by proposal id. Off-box callers never
            # reach this: the id is not a secret, the token is.
            if PHONE and not self.loopback():
                self.send_error(403, "use the per-approval link")
                return
            pid, verb = parts[0], parts[1]
        else:
            self.send_error(404)
            return
        decision = "approve" if verb == "approve" else "reject"
        try:
            platform("POST", f"/v1/tenants/{TENANT}/proposals/{pid}/decide", {
                "decision": decision,
                "note": f"first-touch browser {decision}",
            })
            if tok:
                # Consumed on the first decision, so the link cannot be reused
                # or forwarded to decide something later.
                spend(tok)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(self.wrap(
                    f"<section><h2>Recorded: {html_escape(decision)}</h2>"
                    "<p>This link is now spent. The laptop has the result.</p></section>"
                ).encode("utf-8"))
                return
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        except urllib.error.HTTPError as exc:
            self.send_error(exc.code, exc.read().decode("utf-8"))
        except Exception as exc:
            self.send_error(502, str(exc))

    def log_message(self, fmt, *args):
        print("approval-server:", fmt % args)


def lan_address():
    """The address a phone on the same network would use to reach this laptop."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))   # TEST-NET-1: routed nowhere, sends nothing
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


PORT = int(os.environ.get("FIRST_TOUCH_APPROVAL_PORT", "18054"))
LAN_HOST = lan_address() if PHONE else "127.0.0.1"

if __name__ == "__main__":
    bind = "0.0.0.0" if PHONE else "127.0.0.1"
    if PHONE:
        print(f"approval-server: reachable on this network at http://{LAN_HOST}:{PORT}")
    ThreadingHTTPServer((bind, PORT), Handler).serve_forever()
