#!/usr/bin/env python3
"""ryBlock wall — serves the OFF LIMITS page for every blocked request.

Plain HTTP on :80 always. With --https, also listens on :443 and mints a
per-domain TLS cert on first contact (signed by the local mkcert CA) via an
SNI callback, so https://facebook.com shows the neon page instead of a cert
error — provided `mkcert -install` has trusted the local CA.

usage: blockd.py <blocked.html> [--daemon] [--port N]
                 [--https] [--https-port N] [--cert-dir DIR]
                 [--caroot DIR] [--mkcert PATH]
"""
import os
import socket
import ssl
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PIDFILE = "/var/run/ryblock.pid"


def parse_args(argv):
    o = {
        "page": None, "daemon": False, "port": 80,
        "https": False, "https_port": 443,
        "cert_dir": None, "caroot": None, "mkcert": "mkcert",
    }
    it = iter(argv)
    for a in it:
        if a == "--daemon":
            o["daemon"] = True
        elif a == "--https":
            o["https"] = True
        elif a == "--port":
            o["port"] = int(next(it))
        elif a == "--https-port":
            o["https_port"] = int(next(it))
        elif a == "--cert-dir":
            o["cert_dir"] = next(it)
        elif a == "--caroot":
            o["caroot"] = next(it)
        elif a == "--mkcert":
            o["mkcert"] = next(it)
        else:
            o["page"] = a
    if o["page"] is None:
        sys.exit(__doc__)
    if o["https"] and not o["cert_dir"]:
        sys.exit("--https requires --cert-dir")
    return o


def daemonize():
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)


class CertMinter:
    """Generates & caches per-domain certs signed by the local mkcert CA."""

    def __init__(self, cert_dir, caroot, mkcert):
        self.cert_dir = cert_dir
        self.mkcert = mkcert
        self.env = dict(os.environ)
        if caroot:
            self.env["CAROOT"] = caroot
        self._ctx_cache = {}
        self._lock = threading.Lock()
        os.makedirs(cert_dir, exist_ok=True)

    def _paths(self, domain):
        safe = domain.replace("*", "_wild_")
        return (
            os.path.join(self.cert_dir, f"{safe}.pem"),
            os.path.join(self.cert_dir, f"{safe}-key.pem"),
        )

    def _generate(self, domain, cert, key):
        # cover apex, www, and one wildcard level in a single cert
        names = [domain, f"www.{domain}", f"*.{domain}"]
        subprocess.run(
            [self.mkcert, "-cert-file", cert, "-key-file", key, *names],
            env=self.env, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def context_for(self, domain):
        with self._lock:
            if domain in self._ctx_cache:
                return self._ctx_cache[domain]
            cert, key = self._paths(domain)
            if not (os.path.exists(cert) and os.path.exists(key)):
                self._generate(domain, cert, key)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert, key)
            self._ctx_cache[domain] = ctx
            return ctx


def make_handler(page):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _respond(self, body):
            self.send_response(403)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            if body:
                self.wfile.write(page)

        def do_GET(self):
            self._respond(True)

        def do_HEAD(self):
            self._respond(False)

        do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_GET

        def log_message(self, *a):
            pass

    return Handler


class HTTPServerV6(ThreadingHTTPServer):
    address_family = socket.AF_INET6


def make_server(host, port, https, minter, handler_cls):
    cls = HTTPServerV6 if ":" in host else ThreadingHTTPServer
    server = cls((host, port), handler_cls)
    if https:
        # fallback cert for connections with no SNI; per-domain certs are
        # swapped in by the sni callback
        fallback = minter.context_for("localhost")

        def sni(sock, servername, ctx):
            try:
                if servername:
                    sock.context = minter.context_for(servername)
            except Exception:
                pass  # keep fallback context; worst case a cert warning

        fallback.sni_callback = sni
        server.socket = fallback.wrap_socket(server.socket, server_side=True)
    return server


def main():
    o = parse_args(sys.argv[1:])
    with open(o["page"], "rb") as f:
        page = f.read()
    handler_cls = make_handler(page)

    minter = None
    if o["https"]:
        minter = CertMinter(o["cert_dir"], o["caroot"], o["mkcert"])

    # Browsers resolve blocked domains to BOTH 127.0.0.1 and ::1 (the hosts
    # file maps both) and Chromium/Arc often try ::1 first — so we must listen
    # on IPv4 and IPv6 loopback, else the browser gets connection-refused.
    specs = [("127.0.0.1", o["port"], False), ("::1", o["port"], False)]
    if o["https"]:
        specs += [("127.0.0.1", o["https_port"], True),
                  ("::1", o["https_port"], True)]

    # bind everything before daemonizing so port conflicts fail in the caller.
    # v4 is required; v6 is best-effort (host may have IPv6 disabled).
    servers = []
    for host, port, https in specs:
        try:
            servers.append(make_server(host, port, https, minter, handler_cls))
        except OSError as e:
            if host == "127.0.0.1":
                sys.exit(f"ryBlock: cannot bind {host}:{port} — {e}")
            # ::1 unavailable: skip quietly, v4 still covers most clients

    if o["daemon"]:
        daemonize()

    threads = [threading.Thread(target=s.serve_forever, daemon=True)
               for s in servers]
    for t in threads:
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        pass
    finally:
        if o["daemon"] and os.path.exists(PIDFILE):
            os.remove(PIDFILE)


if __name__ == "__main__":
    main()
